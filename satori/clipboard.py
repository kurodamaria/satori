"""Robust Windows clipboard image reader.

PIL's ImageGrab.grabclipboard() is fragile: when the clipboard carries the
image in the "PNG" format (as Windows 11's Snipping Tool does) it can raise
SyntaxError instead of falling back. This module reads the raw formats via
ctypes and never raises.
"""

from __future__ import annotations

import ctypes
import io
import struct
import sys
from ctypes import wintypes

from PIL import Image

CF_BITMAP = 2
CF_DIB = 8
CF_DIBV5 = 17
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

_user32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
_user32.RegisterClipboardFormatW.restype = wintypes.UINT
_user32.OpenClipboard.argtypes = [wintypes.HWND]
_user32.OpenClipboard.restype = wintypes.BOOL
_user32.GetClipboardData.argtypes = [wintypes.UINT]
_user32.GetClipboardData.restype = wintypes.HANDLE
_user32.CloseClipboard.argtypes = []
_user32.CloseClipboard.restype = wintypes.BOOL
_kernel32.GlobalSize.argtypes = [wintypes.HANDLE]
_kernel32.GlobalSize.restype = ctypes.c_size_t
_kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
_kernel32.GlobalLock.restype = wintypes.LPVOID
_kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
_kernel32.GlobalUnlock.restype = wintypes.BOOL


def _get_clipboard_data(fmt: int) -> bytes | None:
    if not _user32.OpenClipboard(None):
        return None
    try:
        handle = _user32.GetClipboardData(fmt)
        if not handle:
            return None
        size = _kernel32.GlobalSize(handle)
        if not size:
            return None
        ptr = _kernel32.GlobalLock(handle)
        if not ptr:
            return None
        try:
            return ctypes.string_at(ptr, size)
        finally:
            _kernel32.GlobalUnlock(handle)
    finally:
        _user32.CloseClipboard()


def _png_to_image(data: bytes) -> Image.Image | None:
    if data[:8] != PNG_MAGIC:
        return None
    try:
        return Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        return None


def _dib_to_image(data: bytes) -> Image.Image | None:
    """Parse a DIB/DIBV5 stream (BI_RGB / BI_BITFIELDS, 24/32 bpp)."""
    if len(data) < 40:
        return None
    size = struct.unpack_from("<I", data, 0)[0]
    if size not in (40, 108, 124):  # BITMAPINFOHEADER / V4 / V5
        return None
    width = struct.unpack_from("<i", data, 4)[0]
    height = struct.unpack_from("<i", data, 8)[0]
    bpp = struct.unpack_from("<H", data, 14)[0]
    compression = struct.unpack_from("<I", data, 16)[0]
    if width <= 0 or height == 0 or bpp not in (24, 32):
        return None
    if compression not in (0, 3):  # BI_RGB, BI_BITFIELDS
        return None

    top_down = height < 0
    height = abs(height)
    raw_mode, mode = (("BGRA", "RGBA") if bpp == 32 else ("BGR", "RGB"))
    stride = width * (bpp // 8)
    if bpp == 24:
        stride = ((width * 3 + 3) // 4) * 4

    pixels = data[size:]
    required = height * stride
    if len(pixels) < required:
        return None
    pixels = pixels[:required]

    if not top_down:  # bottom-up storage: flip rows
        rows = [pixels[i * stride:(i + 1) * stride] for i in range(height)]
        pixels = b"".join(reversed(rows))

    img = Image.frombytes(mode, (width, height), pixels, "raw", raw_mode)
    return img.convert("RGB")


def read_clipboard_image() -> Image.Image | None:
    """Return the image on the clipboard as an RGB PIL Image, or None."""
    if sys.platform == "win32":
        img = _read_win32()
        if img is not None:
            return img
    # Non-Windows fallback.
    try:
        from PIL import ImageGrab

        got = ImageGrab.grabclipboard()
        if isinstance(got, Image.Image):
            return got.convert("RGB")
    except Exception:
        pass
    return None


def _read_win32() -> Image.Image | None:
    png_fmt = _user32.RegisterClipboardFormatW("PNG")
    # PNG first: Snipping Tool stores a valid PNG there (with alpha).
    if png_fmt:
        data = _get_clipboard_data(png_fmt)
        if data:
            img = _png_to_image(data)
            if img is not None:
                return img
    # Then raw DIB / DIBV5.
    for fmt in (CF_DIBV5, CF_DIB):
        data = _get_clipboard_data(fmt)
        if data:
            img = _dib_to_image(data)
            if img is not None:
                return img
    return None
