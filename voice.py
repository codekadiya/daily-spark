"""Read a quote aloud with tts-1. One voice for every quote, so a first play is a single fast call."""

from quote import client

TTS_MODEL = "tts-1"
VOICE = "fable"  # warm storyteller; other options: alloy, echo, onyx, nova, shimmer


def speak(text: str, theme: str | None = None) -> tuple[bytes, str, str]:
    """Returns (audio_bytes, mime_type, voice)."""
    resp = client.with_options(timeout=30, max_retries=1).audio.speech.create(
        model=TTS_MODEL, voice=VOICE, input=text, response_format="mp3", speed=0.95,
    )
    data = resp.read() if hasattr(resp, "read") else resp.content
    mime = "audio/mpeg"
    if data[:4] == b"RIFF":
        mime = "audio/wav"
    elif data[:4] == b"OggS":
        mime = "audio/ogg"
    return data, mime, VOICE
