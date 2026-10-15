"""Postgres storage for quotes and votes. Uses DATABASE_URL (injected by Roar)."""

import os

import psycopg
from psycopg.rows import dict_row

SCHEMA = """
CREATE TABLE IF NOT EXISTS quotes (
    id         BIGSERIAL PRIMARY KEY,
    text       TEXT NOT NULL,
    theme      TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS votes (
    quote_id   BIGINT NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
    voter_id   TEXT   NOT NULL,
    value      SMALLINT NOT NULL CHECK (value IN (-1, 1)),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (quote_id, voter_id)
);
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS image      BYTEA;
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS image_type TEXT;
"""

# Up, down and the current visitor's own vote for each quote.
SELECT_QUOTES = """
SELECT q.id, q.text, q.theme, q.created_at, (q.image IS NOT NULL) AS has_image,
       COALESCE(SUM(CASE WHEN v.value = 1 THEN 1 END), 0)::int  AS up,
       COALESCE(SUM(CASE WHEN v.value = -1 THEN 1 END), 0)::int AS down,
       COALESCE(MAX(CASE WHEN v.voter_id = %(voter)s THEN v.value END), 0)::int AS my_vote
FROM quotes q
LEFT JOIN votes v ON v.quote_id = q.id
{where}
GROUP BY q.id
{order}
"""


def connect():
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row, autocommit=True)


def init():
    with connect() as conn:
        conn.execute(SCHEMA)
        # One-time clean slate for the painting release. The marker row makes
        # sure this runs exactly once, never on later restarts or deploys.
        conn.execute("CREATE TABLE IF NOT EXISTS migrations (name TEXT PRIMARY KEY, ran_at TIMESTAMPTZ NOT NULL DEFAULT now())")
        with conn.transaction():
            done = conn.execute(
                "INSERT INTO migrations (name) VALUES ('2026-10-clear-for-paintings') ON CONFLICT DO NOTHING RETURNING name"
            ).fetchone()
            if done:
                conn.execute("TRUNCATE votes, quotes RESTART IDENTITY")
                print("migration: cleared old quotes for the painting release", flush=True)


def _shape(row):
    row["score"] = row["up"] - row["down"]
    row["created_at"] = row["created_at"].isoformat()
    return row


def list_quotes(voter, limit=300):
    sql = SELECT_QUOTES.format(
        where="",
        order="ORDER BY (COALESCE(SUM(v.value), 0)) DESC, q.created_at DESC LIMIT %(limit)s",
    )
    with connect() as conn:
        return [_shape(r) for r in conn.execute(sql, {"voter": voter, "limit": limit})]


def get_quote(quote_id, voter):
    sql = SELECT_QUOTES.format(where="WHERE q.id = %(id)s", order="")
    with connect() as conn:
        row = conn.execute(sql, {"voter": voter, "id": quote_id}).fetchone()
    return _shape(row) if row else None


def add_quote(text, theme, voter, image=None, image_type=None):
    with connect() as conn:
        qid = conn.execute(
            "INSERT INTO quotes (text, theme, image, image_type) VALUES (%s, %s, %s, %s) RETURNING id",
            (text, theme, image, image_type),
        ).fetchone()["id"]
    return get_quote(qid, voter)


def get_image(quote_id):
    """Returns (bytes, mime) or None."""
    with connect() as conn:
        row = conn.execute(
            "SELECT image, image_type FROM quotes WHERE id=%s AND image IS NOT NULL", (quote_id,)
        ).fetchone()
    return (bytes(row["image"]), row["image_type"] or "image/jpeg") if row else None


def set_vote(quote_id, voter, value):
    """value 1 or -1 sets the vote, 0 removes it. Returns the updated quote or None."""
    with connect() as conn:
        if value == 0:
            conn.execute("DELETE FROM votes WHERE quote_id=%s AND voter_id=%s", (quote_id, voter))
        else:
            conn.execute(
                """INSERT INTO votes (quote_id, voter_id, value) VALUES (%s, %s, %s)
                   ON CONFLICT (quote_id, voter_id)
                   DO UPDATE SET value = EXCLUDED.value, updated_at = now()""",
                (quote_id, voter, value),
            )
    return get_quote(quote_id, voter)
