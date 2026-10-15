"""Paint a background image for a quote with the cheapest image model on Roar."""

import base64
import random

from quote import client

MODEL = "gpt-image-1-mini"
QUALITY = "low"          # cheapest tier (~$0.003 per image)
SIZE = "1024x1536"       # portrait; cropped to 4:5 on the card and in downloads

STYLES = [
    "an oil painting with thick impasto brushstrokes",
    "a loose watercolor painting with soft bleeding washes",
    "a gouache painting with flat, matte color shapes",
    "an impressionist painting full of broken color and light",
    "a dreamy pastel drawing with visible chalk texture",
    "a Japanese woodblock-inspired painting with calm, layered planes",
]


def build_prompt(quote: str, theme: str | None) -> str:
    style = random.choice(STYLES)
    about = f' The theme is "{theme}".' if theme else ""
    return (
        f"{style.capitalize()} that captures the mood of this quote: \"{quote}\".{about} "
        "Show an evocative scene or landscape that suggests the idea through atmosphere and "
        "symbolism rather than literally. Rich but harmonious colors, painterly texture, "
        "keep the upper and middle areas calm and uncluttered. "
        "Absolutely no text, letters, words, numbers, signatures or watermarks anywhere."
    )


def paint(quote: str, theme: str | None) -> tuple[bytes, str]:
    """Returns (image_bytes, mime_type)."""
    prompt = build_prompt(quote, theme)
    try:
        resp = client.images.generate(
            model=MODEL, prompt=prompt, size=SIZE, quality=QUALITY, n=1,
            output_format="jpeg", output_compression=82,
        )
        mime = "image/jpeg"
    except Exception:
        # Some gateways don't accept output_format; fall back to the default (PNG).
        resp = client.images.generate(model=MODEL, prompt=prompt, size=SIZE, quality=QUALITY, n=1)
        mime = "image/png"
    item = resp.data[0]
    if getattr(item, "b64_json", None):
        data = base64.b64decode(item.b64_json)
    else:  # URL response
        import urllib.request
        with urllib.request.urlopen(item.url, timeout=60) as r:
            data = r.read()
            mime = r.headers.get_content_type() or mime
    # Trust the bytes over the requested format.
    if data[:3] == b"\xff\xd8\xff":
        mime = "image/jpeg"
    elif data[:8] == b"\x89PNG\r\n\x1a\n":
        mime = "image/png"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        mime = "image/webp"
    return data, mime
