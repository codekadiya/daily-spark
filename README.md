# Daily Spark

Inspirational quotes from `gpt-oss-20b` via Roar AI, each with a painting from
`gpt-image-1-mini` (low quality, ~$0.003 each). Every quote and painting is saved to Postgres,
and visitors vote with thumbs up or down (one vote per browser). Top voted shows first.

- `python app.py`: web app at http://localhost:8000
- `python quote.py [theme]`: print one quote in the terminal

Environment: `ROAR_API_KEY` and `DATABASE_URL` (both injected automatically on Roar;
put them in `.env` to run locally). Tables are created on startup.

API
- `GET /api/quotes`: all quotes, ranked by up minus down, newest first on ties
- `POST /api/quotes` `{"theme": "travel"}`: make and save a quote (8 per 10 min per IP)
- `GET /api/quotes/<id>/image`: the quote's painting
- `GET /api/quotes/<id>/audio`: the quote read aloud by `tts-1` (~$0.002, made on first play, then cached in the database)
- `POST /api/quotes/<id>/vote` `{"value": 1 | -1 | 0}`: set or clear your vote

Downloads are composed in the browser: 1080x1350 JPEG with the painting, quote and a Daily Spark mark.

Narration voice is picked per quote by `gpt-oss-20b` from tts-1's six voices to match its mood (see `voice.py`).
