"""Rendering of OCR + translation results."""

from __future__ import annotations

from typing import Optional

import pyperclip


def print_ocr(text: str, raw: bool = False) -> None:
    """Always show the OCR result, even when translation fails."""
    if raw:
        print(text, flush=True)
    else:
        print("--- OCR (JA) ---")
        print(text, flush=True)


def render_result(translation: str, raw: bool = False,
                  clipboard: bool = False) -> Optional[str]:
    """Print the translation; optionally copy it to the clipboard.

    In raw mode only the translated text is printed (machine-friendly).
    Returns the copied string if any.
    """
    if raw:
        print(translation, flush=True)
    else:
        print()
        print("--- Translation ---")
        print(translation, flush=True)

    if clipboard and translation:
        pyperclip.copy(translation)
        return translation
    return None


def format_analysis(result: dict, raw: bool = False) -> str:
    """Build the multi-line tutor output from an llm.analyze() result."""
    if not result.get("reading") and not result.get("similar"):
        return result.get("meaning") or ""
    lines = [result.get("reading", "")]
    lines.append("")
    lines.append(result.get("meaning", ""))
    similar = result.get("similar", [])
    if similar:
        lines.append("")
        for i, sentence in enumerate(similar, 1):
            lines.append(f"{i}. {sentence}")
    return "\n".join(lines)


def render_analysis(result: dict, raw: bool = False,
                    clipboard: bool = False) -> Optional[str]:
    """Print reading / meaning / similar sentences; optionally copy them.

    In raw mode only the meaning is printed (machine-friendly).
    Returns the copied string if any.
    """
    if raw:
        text = result.get("meaning", "")
        print(text, flush=True)
    else:
        text = format_analysis(result)
        print()
        print("--- Reading (hiragana) ---")
        print(result.get("reading", ""), flush=True)
        print()
        print("--- Meaning ---")
        print(result.get("meaning", ""), flush=True)
        similar = result.get("similar", [])
        if similar:
            print()
            print("--- Similar sentences ---")
            for i, sentence in enumerate(similar, 1):
                print(f"{i}. {sentence}", flush=True)

    if clipboard and text:
        pyperclip.copy(text)
        return text
    return None
