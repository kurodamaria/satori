"""Screen capture and interactive freehand (lasso) selection."""

from __future__ import annotations

import tkinter as tk
from typing import Optional

import mss
from PIL import Image, ImageDraw, ImageEnhance, ImageTk


def capture_screen() -> Image.Image:
    """Capture the primary monitor as a physical-pixel RGB image."""
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[1])
    return Image.frombytes("RGB", shot.size, shot.rgb)


def lasso_select(screen: Image.Image) -> Optional[tuple[list, dict]]:
    """Fullscreen overlay: draw a freehand area, then release.

    Returns (points, bbox) in physical screen coordinates, or None if
    cancelled (Esc) or too small.
    """
    phys_w, phys_h = screen.size

    root = tk.Tk()
    log_w, log_h = root.winfo_screenwidth(), root.winfo_screenheight()
    sx = phys_w / log_w
    sy = phys_h / log_h

    root.title("Satori - draw an area, release to capture (Esc = cancel)")
    root.attributes("-fullscreen", True)
    root.attributes("-topmost", True)
    root.configure(cursor="crosshair")

    canvas = tk.Canvas(root, width=log_w, height=log_h, highlightthickness=0,
                       bg="black")
    canvas.pack(fill="both", expand=True)

    dim = ImageEnhance.Brightness(screen).enhance(0.4).resize(
        (log_w, log_h), Image.LANCZOS)
    canvas.photo = ImageTk.PhotoImage(dim)
    canvas.create_image(0, 0, image=canvas.photo, anchor="nw")

    points: list[tuple[int, int]] = []
    line_ids: list[int] = []

    def add_point(event) -> tuple[int, int]:
        """Convert logical tk coords to physical screen coords."""
        pt = (round(event.x * sx), round(event.y * sy))
        points.append(pt)
        return pt

    def on_press(event):
        points.clear()
        for lid in line_ids:
            canvas.delete(lid)
        line_ids.clear()
        add_point(event)

    def on_drag(event):
        if not points:
            return
        add_point(event)
        x1, y1 = points[-2]
        x2, y2 = points[-1]
        line_ids.append(canvas.create_line(x1 / sx, y1 / sy, x2 / sx, y2 / sy,
                                           fill="cyan", width=2))

    def on_release(event):
        if len(points) >= 3:
            x1, y1 = points[-1]
            x0, y0 = points[0]
            line_ids.append(canvas.create_line(x1 / sx, y1 / sy, x0 / sx, y0 / sy,
                                               fill="cyan", width=2))
            root.destroy()
        else:
            points.clear()
            for lid in line_ids:
                canvas.delete(lid)
            line_ids.clear()

    def on_cancel(_event):
        points.clear()
        root.destroy()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Escape>", on_cancel)

    root.mainloop()

    if len(points) < 3:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    bbox = {
        "left": min(xs),
        "top": min(ys),
        "width": max(xs) - min(xs),
        "height": max(ys) - min(ys),
    }
    return points, bbox


def crop_lasso(screen: Image.Image, points: list, bbox: dict) -> Image.Image:
    """Crop the lasso area; outside the polygon is whitened out."""
    left, top = bbox["left"], bbox["top"]
    w, h = bbox["width"], bbox["height"]
    if w < 1 or h < 1:
        raise ValueError("Selection too small")
    region = screen.crop((left, top, left + w, top + h))
    shifted = [(x - left, y - top) for x, y in points]
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).polygon(shifted, fill=255)
    out = Image.new("RGB", (w, h), "white")
    out.paste(region, (0, 0), mask)
    return out


def crop_rect(screen: Image.Image, bbox: dict) -> Image.Image:
    """Crop a rectangular region (for non-interactive capture)."""
    left, top = bbox["left"], bbox["top"]
    w, h = bbox["width"], bbox["height"]
    return screen.crop((left, top, left + w, top + h))
