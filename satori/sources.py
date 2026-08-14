"""Polling sources that hand new images to the translation pipeline.

A source is anything with ``poll() -> Image | None``: it returns an image
only when something new appeared, and ``None`` otherwise.
"""

from __future__ import annotations

import hashlib
import time

from PIL import Image


def _sha(img: Image.Image) -> str:
    return hashlib.sha256(img.tobytes()).hexdigest()


class ClipboardSource:
    """Emits an image whenever a new one lands on the clipboard."""

    def __init__(self, interval: float = 0.4) -> None:
        self.interval = interval
        self._last: str | None = None

    def seed(self) -> str | None:
        """Record whatever is on the clipboard now so it is ignored."""
        from .clipboard import read_clipboard_image

        img = read_clipboard_image()
        self._last = _sha(img) if img is not None else None
        return self._last

    def poll(self) -> Image.Image | None:
        from .clipboard import read_clipboard_image

        img = read_clipboard_image()
        if img is None:
            return None
        h = _sha(img)
        if h == self._last:
            return None
        self._last = h
        return img


class RegionSource:
    """Emits a screen region whenever its pixels change.

    The first poll always emits (so the currently visible content is
    translated right away); afterwards it only reacts to changes, which
    makes it suitable for scrolling through pages or anime frames.
    """

    def __init__(self, bbox: dict, interval: float = 1.0) -> None:
        self.bbox = bbox
        self.interval = interval
        self._last: str | None = None

    def poll(self) -> Image.Image | None:
        import mss
        from PIL import Image as _Image

        with mss.mss() as sct:
            shot = sct.grab({
                "left": int(self.bbox["left"]),
                "top": int(self.bbox["top"]),
                "width": max(1, int(self.bbox["width"])),
                "height": max(1, int(self.bbox["height"])),
            })
        img = _Image.frombytes("RGB", shot.size, shot.rgb)
        h = _sha(img)
        if h == self._last:
            return None
        self._last = h
        return img


def sleep_interval(interval: float) -> None:
    time.sleep(interval)
