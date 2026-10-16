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


# Primary model first; if it's slow or erroring, fall back to the next one.
TEXT_MODELS = [MODEL, "llama-3.1-8b"]


def chat(messages, max_tokens=800, timeouts=(20, 15)) -> str:
    """Chat completion with fallback. timeouts[i] is the wait for TEXT_MODELS[i]."""
    last = None
    for model, timeout in zip(TEXT_MODELS, timeouts):
        try:
            resp = client.with_options(timeout=timeout, max_retries=0).chat.completions.create(
                model=model, messages=messages, max_tokens=max_tokens,
            )
            text = (resp.choices[0].message.content or "").strip()
            if text:
                return text
            last = RuntimeError(f"{model} returned nothing")
        except Exception as e:
            last = e
            print(f"{model} failed ({type(e).__name__}), trying next model", flush=True)
    raise last


def generate_quote(theme: str | None = None) -> str:
    topic = f" about {theme}" if theme else ""
    text = chat([
        {
            "role": "system",
            "content": "You write short, original inspirational quotes. "
            "Reply with the quote only: one or two sentences, no quotation "
            "marks, no attribution, no preamble.",
        },
        {"role": "user", "content": f"Give me one inspirational quote{topic}."},
    ])
    return text.strip('"\u201c\u201d ').strip()


if __name__ == "__main__":
    theme = " ".join(sys.argv[1:]) or None
    print(generate_quote(theme))
