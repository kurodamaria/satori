"""Text-to-speech via a local VOICEVOX engine (anime-style Japanese voices).

VOICEVOX is a free, local Japanese TTS with anime-style characters such as
ずんだもん and 四国めたん. It runs as an HTTP engine (default port 50021);
see https://voicevox.hiroshiba.jp/ to install it. No API key, no network.
"""

from __future__ import annotations

import sys
import threading
from typing import Optional

import requests

DEFAULT_URL = "http://127.0.0.1:50021"
DEFAULT_VOICE = "ずんだもん"

_speakers_cache: list | None = None
_speakers_lock = threading.Lock()


def list_voices(url: str = DEFAULT_URL) -> list[dict]:
    """Query /speakers: [{name, styles: [{name, id}]}]."""
    global _speakers_cache
    with _speakers_lock:
        if _speakers_cache is None:
            try:
                r = requests.get(f"{url}/speakers", timeout=5)
                r.raise_for_status()
            except requests.RequestException as exc:
                raise RuntimeError(
                    f"Cannot reach VOICEVOX at {url} "
                    f"(is the engine running?). Detail: {exc}"
                ) from exc
            _speakers_cache = r.json()
        return _speakers_cache


def reset_voices() -> None:
    global _speakers_cache
    with _speakers_lock:
        _speakers_cache = None


def resolve_voice_id(spec: Optional[str | int], url: str = DEFAULT_URL) -> int:
    """Turn a configured voice (style id, name, or None) into a style id."""
    speakers = list_voices(url)
    if spec is None:
        spec = DEFAULT_VOICE
    if isinstance(spec, int):
        return spec
    name = str(spec).strip()
    if name.isdigit():
        return int(name)
    for spk in speakers:
        spk_name = spk.get("name", "")
        if name == spk_name or name in spk_name:
            return spk["styles"][0]["id"]
        for st in spk["styles"]:
            if name == st.get("name") or name == f"{spk_name} {st.get('name')}":
                return st["id"]
    raise ValueError(
        f"Voice '{name}' not found in VOICEVOX. "
        f"Run `satori voices` to list available voices."
    )


def synthesize(text: str, voice_id: int, url: str = DEFAULT_URL) -> bytes:
    """Return the synthesized WAV bytes for `text` using the given style id."""
    query = requests.post(f"{url}/audio_query",
                          params={"speaker": voice_id},
                          data=text.encode("utf-8"), timeout=30)
    query.raise_for_status()
    wav = requests.post(f"{url}/synthesis",
                        params={"speaker": voice_id},
                        json=query.json(), timeout=120)
    wav.raise_for_status()
    return wav.content


def speak(text: str, voice: Optional[str | int] = None,
          url: str = DEFAULT_URL, blocking: bool = False) -> None:
    """Synthesize `text` with VOICEVOX and play it aloud.

    Non-blocking by default (playback is async, so listening continues).
    Raises RuntimeError/ValueError if the engine is unreachable or the
    voice is unknown.
    """
    text = text.strip()
    if not text:
        return
    if sys.platform != "win32":
        return
    import winsound

    voice_id = resolve_voice_id(voice, url)
    audio = synthesize(text, voice_id, url)
    flags = winsound.SND_MEMORY
    if not blocking:
        flags |= winsound.SND_ASYNC
    winsound.PlaySound(audio, flags)
