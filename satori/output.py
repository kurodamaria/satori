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
