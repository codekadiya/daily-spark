# Daily Spark

Inspirational quotes from `gpt-oss-20b` via Roar AI. Every quote is saved to Postgres,
and visitors vote with thumbs up or down (one vote per browser). Top voted shows first.

- `python app.py`: web app at http://localhost:8000
- `python quote.py [theme]`: print one quote in the terminal

Environment: `ROAR_API_KEY` and `DATABASE_URL` (both injected automatically on Roar;
put them in `.env` to run locally). Tables are created on startup.

API
- `GET /api/quotes`: all quotes, ranked by up minus down, newest first on ties
- `POST /api/quotes` `{"theme": "travel"}`: make and save a quote (8 per 10 min per IP)
- `POST /api/quotes/<id>/vote` `{"value": 1 | -1 | 0}`: set or clear your vote
