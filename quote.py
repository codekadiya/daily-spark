"""Generate an inspirational quote with a cheap GPT model via Roar AI.

    python quote.py                 # random theme
    python quote.py "travel"        # quote on a theme
"""

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

MODEL = "gpt-oss-20b"  # cheapest GPT model on Roar

load_dotenv()
api_key = os.getenv("ROAR_API_KEY")
if not api_key:
    sys.exit("ROAR_API_KEY missing from .env")

client = OpenAI(base_url="https://api.roar-ai.com/v1", api_key=api_key, timeout=120)


def generate_quote(theme: str | None = None) -> str:
    topic = f" about {theme}" if theme else ""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "You write short, original inspirational quotes. "
                "Reply with the quote only: one or two sentences, no quotation "
                "marks, no attribution, no preamble.",
            },
            {"role": "user", "content": f"Give me one inspirational quote{topic}."},
        ],
        max_tokens=800,
    )
    text = (resp.choices[0].message.content or "").strip()
    return text.strip('"“” ').strip()


if __name__ == "__main__":
    theme = " ".join(sys.argv[1:]) or None
    print(generate_quote(theme))
