"""Read a quote aloud with tts-1, in a voice picked to match its mood."""

import re

from quote import MODEL as TEXT_MODEL, client

TTS_MODEL = "tts-1"

# tts-1 voices and the moods they suit, used both for the picker prompt and as a fallback.
VOICES = {
    "alloy":   "balanced, clear, even-toned",
    "echo":    "calm, reflective, gentle male",
    "fable":   "warm, storytelling, expressive",
    "onyx":    "deep, resonant, powerful, steady",
    "nova":    "bright, upbeat, energetic female",
    "shimmer": "soft, soothing, tender female",
}
KEYWORDS = {
    "onyx":    r"\b(strength|strong|power|storm|fight|mountain|courage|fear|endure|rise)\b",
    "nova":    r"\b(joy|bright|sun|sunrise|dance|light|spark|smile|adventure|new)\b",
    "shimmer": r"\b(gentle|quiet|soft|rest|heal|kind|kindness|love|breathe|peace)\b",
    "fable":   r"\b(story|journey|road|path|travel|horizon|map|wander|trail|mile)\b",
    "echo":    r"\b(patience|time|wait|still|silence|slow|reflect|seed|grow)\b",
}


def _fallback(text: str) -> str:
    low = text.lower()
    for voice, pattern in KEYWORDS.items():
        if re.search(pattern, low):
            return voice
    return "alloy"


def pick_voice(text: str, theme: str | None) -> str:
    """Ask the cheap text model which voice fits; fall back to keywords."""
    options = "\n".join(f"- {name}: {mood}" for name, mood in VOICES.items())
    try:
        resp = client.chat.completions.create(
            model=TEXT_MODEL,
            messages=[
                {"role": "system", "content": "You cast narrators. Reply with exactly one voice name from the list, nothing else."},
                {"role": "user", "content": f"Voices:\n{options}\n\nQuote: \"{text}\"\nTheme: {theme or 'none'}\n\nWhich voice fits the quote's mood best?"},
            ],
            max_tokens=400,
        )
        answer = (resp.choices[0].message.content or "").lower()
        for name in VOICES:
            if re.search(rf"\b{name}\b", answer):
                return name
    except Exception as e:
        print(f"voice pick failed, using keywords: {type(e).__name__}", flush=True)
    return _fallback(text)


def speak(text: str, theme: str | None) -> tuple[bytes, str, str]:
    """Returns (audio_bytes, mime_type, voice)."""
    voice = pick_voice(text, theme)
    resp = client.audio.speech.create(
        model=TTS_MODEL, voice=voice, input=text, response_format="mp3", speed=0.95,
    )
    data = resp.read() if hasattr(resp, "read") else resp.content
    mime = "audio/mpeg"
    if data[:4] == b"RIFF":
        mime = "audio/wav"
    elif data[:4] == b"OggS":
        mime = "audio/ogg"
    return data, mime, voice
