"""Configuration handling: API keys (.env) and settings (JSON)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

DEFAULTS: dict[str, Any] = {
    "provider": "deepl",
    "target_lang": "EN",
    "source_lang": "JA",
    "hotkey": "ctrl+shift+t",
    "clipboard_copy": True,
    "save_dir": None,
    "region": None,  # {"left": int, "top": int, "width": int, "height": int}
}


def config_dir() -> Path:
    """Cross-platform per-user config directory."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home())))
        return base / "satori"
    return Path.home() / ".config" / "satori"


def config_path() -> Path:
    return config_dir() / "config.json"


def load_config() -> dict[str, Any]:
    cfg = dict(DEFAULTS)
    path = config_path()
    if path.exists():
        try:
            cfg.update(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(cfg: dict[str, Any]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def load_env() -> None:
    load_dotenv()


def get_api_key(name: str) -> str | None:
    load_env()
    return os.environ.get(name) or None
