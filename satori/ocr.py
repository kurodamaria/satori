"""Manga-specific OCR via manga-ocr (whole image -> Japanese text)."""

from __future__ import annotations

from PIL import Image

_mocr = None


def _get_ocr(threads: int | None = None):
    global _mocr
    if _mocr is None:
        if threads:
            import torch

            torch.set_num_threads(threads)
        from manga_ocr import MangaOcr

        _mocr = MangaOcr()
    return _mocr


def ocr_image(img: Image.Image, threads: int | None = None) -> str:
    """Recognize Japanese text in the image. Multi-line aware."""
    return _get_ocr(threads)(img)
