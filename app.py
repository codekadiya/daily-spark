"""Daily Spark: generate inspirational quotes, store them, and let people vote.

Runs on 0.0.0.0:$PORT (Roar sets PORT; defaults to 8000 locally).
Needs ROAR_API_KEY and DATABASE_URL in the environment (or .env locally).

Routes
  GET  /                        the page
  GET  /health                  liveness check
  GET  /api/quotes              all quotes, top voted first
  POST /api/quotes              {"theme": "..."} -> generate and store a new quote
  POST /api/quotes/<id>/vote    {"value": 1 | -1 | 0} -> set or clear this browser's vote
  GET  /api/quotes/<id>/image   the quote's painting (JPEG/PNG)
  GET  /api/quote?theme=...     legacy: generate and store, returns {"quote": "..."}
"""

import json
import os
import re
import threading
import time
import uuid
from collections import defaultdict, deque
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import psycopg

import db
from painting import paint
from quote import generate_quote

PAGE = (Path(__file__).parent / "index.html").read_text(encoding="utf-8")
COOKIE = "ds_voter"
VOTE_PATH = re.compile(r"^/api/quotes/(\d+)/vote$")
IMAGE_PATH = re.compile(r"^/api/quotes/(\d+)/image$")

# Generation costs money, so cap it per client IP: 8 quotes per 10 minutes.
GEN_LIMIT, GEN_WINDOW = 8, 600
_gen_hits: dict[str, deque] = defaultdict(deque)
_gen_lock = threading.Lock()


def allow_generation(ip: str) -> bool:
    now = time.monotonic()
    with _gen_lock:
        hits = _gen_hits[ip]
        while hits and now - hits[0] > GEN_WINDOW:
            hits.popleft()
        if len(hits) >= GEN_LIMIT:
            return False
        hits.append(now)
        return True


def clean_theme(raw) -> str | None:
    theme = re.sub(r"\s+", " ", str(raw or "")).strip()[:60]
    return theme or None


class Handler(BaseHTTPRequestHandler):
    server_version = "DailySpark"

    # ---- helpers -------------------------------------------------------
    def _voter(self) -> str:
        jar = SimpleCookie(self.headers.get("Cookie", ""))
        vid = jar[COOKIE].value if COOKIE in jar else ""
        if re.fullmatch(r"[0-9a-f]{32}", vid or ""):
            self._new_voter = None
            return vid
        self._new_voter = uuid.uuid4().hex
        return self._new_voter

    def _client_ip(self) -> str:
        fwd = self.headers.get("X-Forwarded-For", "")
        return fwd.split(",")[0].strip() or self.client_address[0]

    def _body(self) -> dict:
        length = min(int(self.headers.get("Content-Length") or 0), 4096)
        if not length:
            return {}
        try:
            data = json.loads(self.rfile.read(length))
            return data if isinstance(data, dict) else {}
        except ValueError:
            return {}

    def _send(self, code, body, ctype="application/json"):
        if not isinstance(body, str):
            body = json.dumps(body)
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        if getattr(self, "_new_voter", None):
            secure = "; Secure" if self.headers.get("X-Forwarded-Proto") == "https" else ""
            self.send_header(
                "Set-Cookie",
                f"{COOKIE}={self._new_voter}; Path=/; Max-Age=63072000; HttpOnly; SameSite=Lax{secure}",
            )
        self.end_headers()
        self.wfile.write(data)

    def _generate(self, theme, voter):
        if not allow_generation(self._client_ip()):
            return 429, {"error": "You've made a lot of quotes. Try again in a few minutes."}
        try:
            text = generate_quote(theme)
        except Exception as e:
            return 502, {"error": f"The quote service didn't respond ({type(e).__name__}). Try again."}
        if not text:
            return 502, {"error": "The quote came back empty. Try again."}
        try:
            image, mime = paint(text, theme)
        except Exception as e:  # keep the quote even if the painting fails
            print(f"painting failed: {type(e).__name__}: {e}", flush=True)
            image, mime = None, None
        return 201, db.add_quote(text, theme, voter, image, mime)

    # ---- routes --------------------------------------------------------
    def do_GET(self):
        url = urlparse(self.path)
        voter = self._voter()
        if url.path == "/":
            self._send(200, PAGE, "text/html; charset=utf-8")
        elif url.path == "/health":
            self._send(200, "ok", "text/plain")
        elif url.path == "/api/quotes":
            self._send(200, {"quotes": db.list_quotes(voter)})
        elif IMAGE_PATH.match(url.path):
            found = db.get_image(int(IMAGE_PATH.match(url.path).group(1)))
            if not found:
                self._send(404, {"error": "No painting for this quote"})
                return
            data, mime = found
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
            self.end_headers()
            self.wfile.write(data)
        elif url.path == "/api/quote":  # legacy endpoint
            theme = clean_theme(parse_qs(url.query).get("theme", [""])[0])
            code, body = self._generate(theme, voter)
            self._send(code, {"quote": body["text"]} if code == 201 else body)
        else:
            self._send(404, {"error": "Not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        voter = self._voter()
        if path == "/api/quotes":
            code, body = self._generate(clean_theme(self._body().get("theme")), voter)
            self._send(code, body)
            return
        m = VOTE_PATH.match(path)
        if m:
            value = self._body().get("value")
            if value not in (1, -1, 0):
                self._send(400, {"error": "value must be 1, -1 or 0"})
                return
            try:
                quote = db.set_vote(int(m.group(1)), voter, value)
            except psycopg.errors.ForeignKeyViolation:
                quote = None
            self._send(200, quote) if quote else self._send(404, {"error": "Quote not found"})
            return
        self._send(404, {"error": "Not found"})

    def log_message(self, fmt, *args):  # quieter logs: skip health checks
        if "/health" not in (args[0] if args else ""):
            super().log_message(fmt, *args)


if __name__ == "__main__":
    db.init()
    port = int(os.getenv("PORT", "8000"))
    print(f"Listening on 0.0.0.0:{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
