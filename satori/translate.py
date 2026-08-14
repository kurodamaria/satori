"""Cloud translation backends: DeepL (default) and Google."""

from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import get_api_key

DEEPL_API_URL = "https://api-free.deepl.com/v2/translate"


def translate(text: str, provider: str = "deepl", target_lang: str = "EN",
              source_lang: str = "JA") -> str:
    text = text.strip()
    if not text:
        return ""
    if provider == "google":
        return _translate_google(text, target_lang)
    return _translate_deepl(text, target_lang, source_lang)


def _translate_deepl(text: str, target_lang: str, source_lang: str) -> str:
    api_key = get_api_key("DEEPL_API_KEY")
    if not api_key:
        raise RuntimeError(
            "DEEPL_API_KEY not set. Add it to a .env file in the project root "
            "(see .env.example) or set the environment variable."
        )
    body = urlencode({
        "auth_key": api_key,
        "text": text,
        "target_lang": target_lang,
        "source_lang": source_lang,
    }).encode()
    req = Request(DEEPL_API_URL, data=body)
    with urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["translations"][0]["text"]


def _translate_google(text: str, target_lang: str) -> str:
    api_key = get_api_key("GOOGLE_API_KEY")
    if api_key:
        return _translate_google_cloud(text, target_lang, api_key)
    return _translate_google_free(text, target_lang)


def _translate_google_cloud(text: str, target_lang: str, api_key: str) -> str:
    body = json.dumps({"q": [text], "target": target_lang.lower()}).encode()
    req = Request(
        "https://translation.googleapis.com/language/translate/v2",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    req.add_unredirected_header("X-goog-api-key", api_key)
    with urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["data"]["translations"][0]["translatedText"]


def _translate_google_free(text: str, target_lang: str) -> str:
    from deep_translator import GoogleTranslator

    return GoogleTranslator(source="auto", target=target_lang.lower()).translate(text)
