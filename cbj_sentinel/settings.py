"""User settings, data directory, logging, and Windows auto-start."""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Any, Dict

from . import config

DEFAULTS: Dict[str, Any] = {
    "sound": True,
    "opponent_sound": False,
    "auto_popup": True,
    "popup_on_goal": True,
    "toasts": True,
    "puck_drop_reminder": True,
    "spoiler_mode": False,
    "mini_overlay": True,
    "ticker_bar": False,
    "start_with_windows": False,
    "tray_live_score": False,
    "delay_seconds": 0,
    "volume": 80,
    "watch": config.DEFAULT_WATCH,
    "overlay_x": -1,
    "overlay_y": -1,
    "ticker_x": -1,
    "ticker_y": -1,
}
LIMITS = {
    "delay_seconds": (0, 180),
    "volume": (0, 100),
    "overlay_x": (-1, 20000),
    "overlay_y": (-1, 20000),
    "ticker_x": (-1, 20000),
    "ticker_y": (-1, 20000),
}
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    path = Path(base) / config.APP_ID
    path.mkdir(parents=True, exist_ok=True)
    return path


def setup_logging() -> None:
    handler = logging.handlers.RotatingFileHandler(
        data_dir() / "sentinel.log", maxBytes=256 * 1024, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def sanitize(raw: Any) -> Dict[str, Any]:
    settings = dict(DEFAULTS)
    if not isinstance(raw, dict):
        return settings
    for key, default in DEFAULTS.items():
        value = raw.get(key)
        if type(value) is not type(default):   # strict: True is not accepted as an int
            continue
        if key in LIMITS:
            lo, hi = LIMITS[key]
            value = max(lo, min(hi, value))
        if key == "watch" and value not in config.WATCH_OPTIONS:
            continue
        settings[key] = value
    return settings


def load() -> Dict[str, Any]:
    try:
        return sanitize(json.loads((data_dir() / "settings.json").read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return dict(DEFAULTS)


def save(settings: Dict[str, Any]) -> None:
    clean = sanitize(settings)
    path = data_dir() / "settings.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(clean, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def autostart_command() -> str:
    if getattr(sys, "frozen", False):  # PyInstaller build
        return f'"{sys.executable}" --minimized'
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    launcher = Path(__file__).resolve().parent.parent / "run_sentinel.pyw"
    return f'"{pythonw if pythonw.exists() else exe}" "{launcher}" --minimized'


def set_autostart(enabled: bool) -> bool:
    """Register/unregister in HKCU Run (per-user, no admin rights needed)."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, config.APP_ID, 0, winreg.REG_SZ, autostart_command())
            else:
                try:
                    winreg.DeleteValue(key, config.APP_ID)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        logging.getLogger(__name__).exception("Could not update auto-start")
        return False
