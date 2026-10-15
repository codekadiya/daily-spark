"""Inspiration Quote web app. Serves a page plus a JSON endpoint.

Runs on 0.0.0.0:$PORT (Roar sets PORT; defaults to 8000 locally).
    python app.py   ->  http://localhost:8000
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from quote import generate_quote

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily Spark</title>
<style>
  :root { --bg:#f6f1e7; --ink:#1f1b16; --muted:#6b6257; --accent:#c4552d; --card:#fffaf2; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#16130f; --ink:#f2ebe0; --muted:#a39886; --accent:#e07a50; --card:#1f1b16; }
  }
  * { box-sizing:border-box; }
  body { margin:0; min-height:100vh; display:grid; place-items:center; background:var(--bg);
         color:var(--ink); font-family: Georgia, "Times New Roman", serif; padding:16px; }
  main { width:100%; max-width:640px; background:var(--card); border-radius:18px; padding:40px 32px;
         box-shadow:0 10px 40px rgba(0,0,0,.08); }
  h1 { margin:0 0 4px; font-size:14px; letter-spacing:.2em; text-transform:uppercase; color:var(--accent);
       font-family: system-ui, sans-serif; }
  #quote { font-size:clamp(22px,4.5vw,32px); line-height:1.35; min-height:3.5em; margin:24px 0 32px; }
  #quote.loading { color:var(--muted); }
  form { display:flex; gap:10px; flex-wrap:wrap; font-family:system-ui, sans-serif; }
  input { flex:1 1 200px; padding:12px 14px; border-radius:10px; border:1px solid var(--muted);
          background:transparent; color:var(--ink); font-size:16px; }
  button { padding:12px 20px; border:0; border-radius:10px; background:var(--accent); color:#fff;
           font-size:16px; cursor:pointer; }
  button:disabled { opacity:.6; cursor:wait; }
</style></head>
<body><main>
  <h1>Daily Spark</h1>
  <p id="quote" class="loading">Fetching a little inspiration…</p>
  <form id="f">
    <input id="theme" placeholder="Theme (optional), e.g. travel" maxlength="60">
    <button id="go">New quote</button>
  </form>
</main>
<script>
  const q = document.getElementById('quote'), btn = document.getElementById('go');
  async function load(theme) {
    btn.disabled = true; q.className = 'loading'; q.textContent = 'Thinking…';
    try {
      const r = await fetch('/api/quote' + (theme ? '?theme=' + encodeURIComponent(theme) : ''));
      const d = await r.json();
      q.className = ''; q.textContent = d.quote || d.error || 'Something went wrong.';
    } catch (e) { q.className = ''; q.textContent = 'Could not reach the server.'; }
    btn.disabled = false;
  }
  document.getElementById('f').addEventListener('submit', e => {
    e.preventDefault(); load(document.getElementById('theme').value.trim());
  });
  load();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/":
            self._send(200, PAGE, "text/html; charset=utf-8")
        elif url.path == "/health":
            self._send(200, "ok", "text/plain")
        elif url.path == "/api/quote":
            theme = (parse_qs(url.query).get("theme", [""])[0] or "").strip()[:60] or None
            try:
                body, code = {"quote": generate_quote(theme)}, 200
            except Exception as e:  # keep the page alive on API errors
                body, code = {"error": f"Quote service error: {type(e).__name__}"}, 502
            self._send(code, json.dumps(body), "application/json")
        else:
            self._send(404, "Not found", "text/plain")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"Listening on 0.0.0.0:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
