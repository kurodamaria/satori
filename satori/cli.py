"""Satori command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

from . import __version__
from .capture import capture_screen, crop_lasso, crop_rect, lasso_select
from .config import load_config, save_config
from .ocr import ocr_image
from .output import print_ocr, render_result
from .translate import translate


def _pipeline(img: Image.Image, cfg: dict, args: argparse.Namespace) -> None:
    provider = args.provider or cfg["provider"]
    target = args.target_lang or cfg["target_lang"]
    source = args.source_lang or cfg["source_lang"]
    save_dir = args.save_dir or cfg["save_dir"]
    if save_dir:
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        img.save(Path(save_dir) / "capture.png")

    text = ocr_image(img, threads=args.threads)

    def _translate() -> str:
        return translate(text, provider=provider, target_lang=target,
                         source_lang=source)

    if args.raw and not args.ocr_only:
        try:
            translation = _translate()
        except Exception as exc:
            print(text, flush=True)
            print(f"Error: {exc}", flush=True)
            return
        render_result(translation, raw=True, clipboard=args.clipboard)
        return

    print_ocr(text, raw=args.raw)
    if args.ocr_only:
        return
    try:
        translation = _translate()
    except Exception as exc:
        print(f"Error: {exc}", flush=True)
        return
    render_result(translation, raw=args.raw, clipboard=args.clipboard)


def _lasso_pipeline(cfg: dict, args: argparse.Namespace) -> int:
    screen = capture_screen()
    result = lasso_select(screen)
    if result is None:
        print("Cancelled.")
        return 1
    points, bbox = result
    img = crop_lasso(screen, points, bbox)
    _pipeline(img, cfg, args)
    return 0


def cmd_capture(args: argparse.Namespace) -> int:
    cfg = load_config()
    if args.x is not None:
        bbox = {"left": args.x, "top": args.y or 0, "width": args.w,
                "height": args.h}
        img = crop_rect(capture_screen(), bbox)
        _pipeline(img, cfg, args)
        return 0
    return _lasso_pipeline(cfg, args)


def cmd_file(args: argparse.Namespace) -> int:
    cfg = load_config()
    img = Image.open(args.path).convert("RGB")
    _pipeline(img, cfg, args)
    return 0


def cmd_listen(args: argparse.Namespace) -> int:
    """Listen to a source (clipboard or screen region) and translate new images."""
    import time

    from .sources import ClipboardSource, RegionSource

    cfg = load_config()
    source_name = getattr(args, "source", None) or "clipboard"

    if source_name == "clipboard":
        source: ClipboardSource | RegionSource = ClipboardSource(interval=0.4)
        print("Listening to clipboard. Use Win+Shift+S to capture "
              "(Ctrl+C to stop)...", flush=True)
        last = source.seed()
        if args.verbose:
            print(f"clipboard image at start: "
                  f"{last[:8] + '...' if last else 'none'}", flush=True)
    else:
        x, y = getattr(args, "x", None), getattr(args, "y", None)
        w, h = getattr(args, "w", None), getattr(args, "h", None)
        if x is not None:
            bbox = {"left": x, "top": y or 0, "width": w, "height": h}
        else:
            result = lasso_select(capture_screen())
            if result is None:
                print("Cancelled.")
                return 1
            _, bbox = result
        interval = getattr(args, "interval", None) or 1.0
        source = RegionSource(bbox, interval=interval)
        print(f"Listening to region {bbox['left']},{bbox['top']} "
              f"{bbox['width']}x{bbox['height']} "
              f"(every {interval:g}s, Ctrl+C to stop)...", flush=True)

    try:
        while True:
            time.sleep(source.interval)
            img = source.poll()
            if img is None:
                continue
            if args.verbose:
                print(f"new image: {img.size} {img.mode}", flush=True)
            try:
                _pipeline(img, cfg, args)
            except Exception as exc:
                print(f"Error: {exc}", flush=True)
    except KeyboardInterrupt:
        pass
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    """Alias for `listen --source clipboard` (kept for compatibility)."""
    args.source = "clipboard"
    return cmd_listen(args)


def cmd_config(args: argparse.Namespace) -> int:
    cfg = load_config()
    for key, value in cfg.items():
        print(f"{key}: {value}")
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    cfg = load_config()
    if args.hotkey:
        cfg["hotkey"] = args.hotkey
        print(f"Hotkey set to '{args.hotkey}'")
    if args.provider:
        cfg["provider"] = args.provider
        print(f"Provider set to '{args.provider}'")
    if args.target_lang:
        cfg["target_lang"] = args.target_lang
        print(f"Target language set to '{args.target_lang}'")
    save_config(cfg)
    return 0


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider", choices=["deepl", "google"])
    parser.add_argument("--target-lang", default=None)
    parser.add_argument("--source-lang", default=None)
    parser.add_argument("--raw", action="store_true",
                        help="print only the translated text")
    parser.add_argument("--no-clipboard", dest="clipboard", action="store_false",
                        help="do not copy translation to clipboard")
    parser.add_argument("--save-dir", default=None,
                        help="directory to save captures for debugging")
    parser.add_argument("--ocr-only", action="store_true",
                        help="skip translation")
    parser.add_argument("--threads", type=int, default=None,
                        help="torch CPU threads (try --threads 8 if OCR stalls)")
    parser.add_argument("--verbose", action="store_true",
                        help="print diagnostics while listening")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="satori",
        description="Satori (悟り) - manga screenshot OCR + translation.",
    )
    parser.add_argument("--version", action="version",
                        version=f"satori {__version__}")
    sub = parser.add_subparsers(dest="command")

    p_capture = sub.add_parser(
        "capture", help="lasso a screen area, OCR and translate")
    _add_common(p_capture)
    p_capture.add_argument("--x", type=int, default=None,
                           help="non-interactive capture: left coordinate")
    p_capture.add_argument("--y", type=int, default=None,
                           help="non-interactive capture: top coordinate")
    p_capture.add_argument("--w", type=int, default=None,
                           help="non-interactive capture: width")
    p_capture.add_argument("--h", type=int, default=None,
                           help="non-interactive capture: height")
    p_capture.set_defaults(func=cmd_capture)

    p_file = sub.add_parser("file", help="OCR + translate an image file")
    _add_common(p_file)
    p_file.add_argument("path", type=Path)
    p_file.set_defaults(func=cmd_file)

    p_watch = sub.add_parser(
        "watch", help="alias for `listen --source clipboard`")
    _add_common(p_watch)
    p_watch.add_argument("--hotkey", default=None)
    p_watch.set_defaults(func=cmd_watch)

    p_listen = sub.add_parser(
        "listen", help="listen to a source (clipboard or screen region), "
                       "OCR + translate new images")
    _add_common(p_listen)
    p_listen.add_argument("--source", choices=["clipboard", "region"],
                          default="clipboard",
                          help="what to listen to (default: clipboard)")
    p_listen.add_argument("--interval", type=float, default=None,
                          help="region poll interval in seconds (default: 1.0)")
    p_listen.add_argument("--x", type=int, default=None,
                          help="non-interactive region: left coordinate")
    p_listen.add_argument("--y", type=int, default=None,
                          help="non-interactive region: top coordinate")
    p_listen.add_argument("--w", type=int, default=None,
                          help="non-interactive region: width")
    p_listen.add_argument("--h", type=int, default=None,
                          help="non-interactive region: height")
    p_listen.set_defaults(func=cmd_listen)

    p_config = sub.add_parser("config", help="show current configuration")
    p_config.set_defaults(func=cmd_config)

    p_set = sub.add_parser("set", help="change configuration values")
    p_set.add_argument("--hotkey", default=None)
    p_set.add_argument("--provider", choices=["deepl", "google"], default=None)
    p_set.add_argument("--target-lang", default=None)
    p_set.set_defaults(func=cmd_set)

    return parser


def _enable_utf8() -> None:
    """Force UTF-8 output so Japanese text survives the Windows console."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError, OSError):
            pass


def main(argv=None) -> int:
    _enable_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
