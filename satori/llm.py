"""LLM analysis via an OpenAI-compatible endpoint (e.g. chat2api).

Instead of a plain translation, the OCR'd Japanese is sent to the LLM with
a tutor prompt that asks for:
- how to read it: the sentence rewritten in pure hiragana, chunk by chunk
- what it means: translation/explanation in the target language
- two similar sentences sharing the same grammatical structure
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional
from urllib.request import Request, urlopen

from .config import get_api_key

DEFAULT_LLM_URL = "http://127.0.0.1:8080"
DEFAULT_LLM_MODEL = "deepseek-v4-flash"

SYSTEM_PROMPT = (
    "You are a Japanese language tutor helping a learner read manga. "
    "The text you receive was produced by OCR from manga speech bubbles, "
    "so it may contain small recognition errors; silently fix obvious ones. "
    "Always answer with a single JSON object and nothing else."
)


def _user_prompt(text: str, target_lang: str) -> str:
    return f"""Japanese text:
{text}

Analyze it and respond ONLY with a JSON object of this exact shape:
{{
  "reading": "<the whole sentence rewritten in pure hiragana (no kanji), split into natural chunks separated by single spaces>",
  "meaning": "<what the sentence means in {target_lang}: a natural translation, plus a brief explanation if it is ambiguous>",
  "similar": [
    "<a new Japanese sentence using the same grammatical structure as the original>",
    "<another one, different vocabulary again but the same structure>"
  ]
}}

Rules:
- "reading": hiragana only; keep particles attached to their word; one space between chunks.
- "similar": exactly two sentences, natural everyday Japanese, roughly the same politeness level as the original.
- Output raw JSON only: no markdown fences, no commentary."""


def _endpoint(base_url: str) -> str:
    base = base_url.rstrip("/")
    if not base.endswith("/v1"):
        base += "/v1"
    return base + "/chat/completions"


def _extract_json(content: str) -> Optional[dict[str, Any]]:
    """Parse the model's answer leniently (tolerates ``` fences)."""
    stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
    try:
        data = json.loads(stripped)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    return None


def _normalize(data: dict[str, Any], raw_text: str) -> dict[str, Any]:
    similar = data.get("similar")
    if isinstance(similar, str):
        similar = [s.strip() for s in re.split(r"\n+", similar) if s.strip()]
    if not isinstance(similar, list):
        similar = []
    return {
        "reading": str(data.get("reading", "")).strip(),
        "meaning": str(data.get("meaning", "")).strip(),
        "similar": [str(s).strip() for s in similar][:2],
        "raw": raw_text,
    }


def analyze(text: str, target_lang: str = "EN",
            base_url: str = DEFAULT_LLM_URL,
            model: str = DEFAULT_LLM_MODEL) -> dict[str, Any]:
    """Ask the LLM for reading / meaning / similar sentences.

    Returns {"reading", "meaning", "similar", "raw"}; on any failure the
    raw completion is returned in "raw" with the other fields empty.
    """
    text = text.strip()
    if not text:
        return {"reading": "", "meaning": "", "similar": [], "raw": ""}

    api_key = get_api_key("LLM_API_KEY") or get_api_key("OPENAI_API_KEY")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    body = json.dumps({
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _user_prompt(text, target_lang)},
        ],
    }).encode()

    req = Request(_endpoint(base_url), data=body, headers=headers)
    with urlopen(req, timeout=180) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    content = payload["choices"][0]["message"]["content"]

    data = _extract_json(content)
    if data is None:
        return {"reading": "", "meaning": content.strip(), "similar": [],
                "raw": content}
    return _normalize(data, content)
