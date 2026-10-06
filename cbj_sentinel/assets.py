"""Original, procedurally generated artwork and audio (no third-party assets).

The built-in goal horn is synthesized from scratch. Its pitch and tone were
modelled on a spectral analysis of how the horn sounds at Nationwide Arena
(a single deep ~138 Hz horn blast followed by the cannon), but no recorded
audio ships with the app. Fans can import their own ``.wav`` from Settings;
it is stored only in %APPDATA%\\CBJGamedaySentinel.
"""
from __future__ import annotations

import io
import logging
import math
import os
import random
import shutil
import sys
import threading
import wave
from array import array
from pathlib import Path
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont

from . import config
from .settings import data_dir

log = logging.getLogger(__name__)

HORN_FILE = "goal_horn_v2.wav"        # bump the name whenever the synth changes
CHIME_FILE = "opponent_chime_v1.wav"
CUSTOM_HORN = "custom_horn.wav"
MAX_IMAGE_PIXELS = 4_000_000

# Relative harmonic amplitudes (1st..20th) measured from arena recordings.
HORN_F0 = 138.0
HORN_HARMONICS = (1.00, .46, .45, .22, .06, .05, .54, .38, .14, .08,
                  .26, .01, .17, .37, .10, .13, .17, .12, .00, .07)

_synth_lock = threading.Lock()


# ------------------------------------------------------------------- artwork
def _star(cx: float, cy: float, r_out: float, r_in: float):
    pts = []
    for i in range(10):
        r = r_out if i % 2 == 0 else r_in
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def load_safe_image(raw: bytes, max_side: int) -> Image.Image:
    """Decode untrusted image bytes defensively and return a thumbnail."""
    img = Image.open(io.BytesIO(raw))
    if img.format not in ("PNG", "JPEG", "WEBP"):
        raise ValueError(f"Unsupported image format {img.format!r}")
    w, h = img.size
    if w <= 0 or h <= 0 or w * h > MAX_IMAGE_PIXELS:
        raise ValueError("Image dimensions out of range")
    img.load()
    img = img.convert("RGBA")
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    return img


TEAM_LOGO = "team_logo.png"
_logo_cache: dict = {}


def team_logo_path() -> Path:
    return data_dir() / TEAM_LOGO


def team_logo_stale() -> bool:
    p = team_logo_path()
    if not p.is_file():
        return True
    import time
    return time.time() - p.stat().st_mtime > config.LOGO_MAX_AGE_DAYS * 86400


def save_team_logo(raw: bytes) -> bool:
    """Validate downloaded logo bytes and cache a re-encoded PNG copy."""
    img = load_safe_image(raw, 512)
    tmp = team_logo_path().with_suffix(".tmp")
    img.save(tmp, format="PNG")
    os.replace(tmp, team_logo_path())
    _logo_cache.clear()
    return True


def _base_logo() -> Optional[Image.Image]:
    if "img" in _logo_cache:
        return _logo_cache["img"]
    img = None
    bundled = Path(__file__).parent / "logo.png"
    for p in (data_dir() / "custom_logo.png", data_dir() / TEAM_LOGO, bundled):
        if p.is_file() and p.stat().st_size <= config.MAX_IMAGE_BYTES:
            try:
                img = load_safe_image(p.read_bytes(), 1024)
                break
            except Exception:
                log.warning("%s could not be loaded", p.name)
    _logo_cache["img"] = img
    return img


def app_icon(size: int = 256) -> Image.Image:
    logo = _base_logo()
    if logo is not None:
        bbox = logo.getbbox()
        if bbox:
            cropped = logo.crop(bbox)
            w, h = cropped.size
            side = max(w, h)
            pad = max(1, int(side * 0.04))
            canvas = Image.new("RGBA", (side + pad * 2, side + pad * 2), (0, 0, 0, 0))
            canvas.paste(cropped, (pad + (side - w) // 2, pad + (side - h) // 2), cropped)
            return canvas.resize((size, size), Image.LANCZOS)
        canvas = Image.new("RGBA", (max(logo.size),) * 2, (0, 0, 0, 0))
        canvas.paste(logo, ((canvas.width - logo.width) // 2, (canvas.height - logo.height) // 2), logo)
        return canvas.resize((size, size), Image.LANCZOS)
    s = size * 4                                   # original fallback art, supersampled
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((s * .03, s * .03, s * .97, s * .97), fill=config.RED)
    d.ellipse((s * .11, s * .11, s * .89, s * .89), fill=config.NAVY)
    d.ellipse((s * .15, s * .15, s * .85, s * .85), outline=config.SILVER, width=max(1, s // 64))
    d.polygon(_star(s / 2, s * .53, s * .31, s * .125), fill="#FFFFFF")
    return img.resize((size, size), Image.LANCZOS)


def _font(px: int) -> ImageFont.ImageFont:
    for name in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    return ImageFont.load_default()


def score_icon(ours: int, theirs: int, size: int = 64) -> Image.Image:
    """Tray icon showing the live score, ring colored by game state."""
    ring = config.GREEN if ours > theirs else (config.RED if ours < theirs else config.SILVER)
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, s - 1, s - 1), fill=ring)
    d.ellipse((s * .08, s * .08, s * .92, s * .92), fill=config.NAVY)
    text = f"{ours}-{theirs}"
    fpx = int(s * .52)
    while fpx > 8:
        font = _font(fpx)
        box = d.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= s * .80:
            break
        fpx -= 4
    w, h = box[2] - box[0], box[3] - box[1]
    d.text(((s - w) / 2 - box[0], (s - h) / 2 - box[1]), text, font=font, fill="#FFFFFF")
    return img.resize((size, size), Image.LANCZOS)


# --------------------------------------------------------------------- audio
def _write_wav(path: Path, samples: List[float], sr: int, level: float = 0.89) -> None:
    peak = max((abs(x) for x in samples), default=0.0) or 1.0
    pcm = array("h", (int(max(-1.0, min(1.0, x / peak * level)) * 32767) for x in samples))
    tmp = path.with_suffix(".tmp")
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    os.replace(tmp, path)


def synth_horn_samples(sr: int = 22050) -> List[float]:
    """Arena-style goal horn (~5 s) followed by a cannon blast with echoes."""
    rnd = random.Random(2007)
    horn_len = 5.15
    total = int((horn_len + 3.3) * sr)
    out = [0.0] * total

    # One period of the horn's measured timbre as a wavetable.
    n_tab = 4096
    phases = [rnd.uniform(0, 2 * math.pi) for _ in HORN_HARMONICS]
    table = [sum(a * math.sin(2 * math.pi * (h + 1) * k / n_tab + phases[h])
                 for h, a in enumerate(HORN_HARMONICS) if a) for k in range(n_tab)]
    tpeak = max(abs(v) for v in table)
    table = [v / tpeak for v in table]

    n_h, rel = int(horn_len * sr), int(0.30 * sr)
    p1 = p2 = 0.0
    breath = 0.0
    vib_w = 2 * math.pi * 5.2 / sr
    step = n_tab / sr
    for i in range(n_h):
        t = i / sr
        f = HORN_F0 * (1.0 - 0.06 * math.exp(-t * 16)) * (1.0 + 0.0025 * math.sin(vib_w * i))
        p1 = (p1 + f * step) % n_tab
        p2 = (p2 + f * 1.0045 * step) % n_tab       # slight detune = big-horn chorus
        breath += 0.05 * (rnd.uniform(-1, 1) - breath)
        env = min(1.0, t / 0.09) * min(1.0, (n_h - i) / rel) * (1.0 + 0.04 * math.sin(4.4 * t))
        v = 0.62 * table[int(p1)] + 0.38 * table[int(p2)] + 0.5 * breath
        out[i] = 0.55 * math.tanh(1.6 * v) * env

    # Cannon: sharp crack, low boom (60-250 Hz) and broadband powder crackle.
    c0 = int((horn_len - 0.05) * sr)
    lp_b = lp_h = phase = 0.0
    for i in range(min(int(2.6 * sr), total - c0)):
        t = i / sr
        w = rnd.uniform(-1, 1)
        lp_b += 0.061 * (w - lp_b)
        lp_h += 0.45 * (w - lp_h)
        phase += 2 * math.pi * (45 + 70 * math.exp(-t * 6)) / sr
        attack = min(1.0, t / 0.004)
        crack = w * math.exp(-t * 80)
        boom = 0.95 * math.sin(phase) * math.exp(-t * 3.0) + 2.8 * lp_b * math.exp(-t * 2.3)
        crackle = 0.0
        if t < 1.1:
            crackle = (w - lp_h) * 0.5 * math.exp(-t * 4.5) * (1.0 if rnd.random() < 0.3 else 0.25)
        out[c0 + i] += attack * (1.1 * crack + boom + crackle)

    # Arena reflections: low-passed multi-tap echo.
    wet, lp = [0.0] * total, 0.0
    for i, x in enumerate(out):
        lp += 0.35 * (x - lp)
        wet[i] = lp
    for delay, gain in ((0.083, .32), (0.161, .24), (0.247, .17), (0.39, .11), (0.58, .07)):
        d = int(delay * sr)
        for i in range(d, total):
            out[i] += gain * wet[i - d]

    # Gentle limiter so the cannon is louder than the horn without clipping.
    peak = max(abs(x) for x in out) or 1.0
    k = math.tanh(1.4)
    return [math.tanh(1.4 * x / peak) / k for x in out]


def synth_chime_samples(sr: int = 22050) -> List[float]:
    """Soft two-note descending chime for opponent goals."""
    out: List[float] = []
    for f, dur in ((659.25, 0.28), (523.25, 0.55)):
        n = int(dur * sr)
        for i in range(n):
            t = i / sr
            env = min(1.0, t / 0.01) * math.exp(-t * 5.5)
            out.append(env * (math.sin(2 * math.pi * f * t) + 0.25 * math.sin(4 * math.pi * f * t)))
    return out


def _ensure(name: str, make, level: float) -> Optional[Path]:
    path = data_dir() / name
    with _synth_lock:
        if not path.is_file():
            try:
                _write_wav(path, make(), 22050, level)
            except Exception:
                log.exception("Could not synthesize %s", name)
                return None
    return path


def prepare_sounds() -> None:
    """Pre-generate sounds (call from a background thread at start-up)."""
    _ensure(HORN_FILE, synth_horn_samples, 0.89)
    _ensure(CHIME_FILE, synth_chime_samples, 0.45)


def validate_wav(path: os.PathLike) -> Optional[str]:
    """Return an error message, or None if the file is a playable PCM WAV."""
    p = Path(path)
    try:
        if not p.is_file():
            return "File not found."
        if p.stat().st_size > config.MAX_CUSTOM_WAV_BYTES:
            return f"File is larger than {config.MAX_CUSTOM_WAV_BYTES // (1024 * 1024)} MB."
        with wave.open(str(p), "rb") as w:
            channels, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
    except (wave.Error, EOFError, OSError):
        return "Not a valid PCM .wav file. Convert it to 16-bit PCM WAV and try again."
    if channels not in (1, 2) or width not in (1, 2) or not 8000 <= rate <= 96000:
        return "Unsupported WAV format (use 16-bit PCM, mono or stereo)."
    if frames / rate > config.MAX_CUSTOM_WAV_SECONDS:
        return f"Clip is longer than {config.MAX_CUSTOM_WAV_SECONDS} seconds."
    return None


def install_custom_horn(src: os.PathLike) -> Optional[str]:
    err = validate_wav(src)
    if err:
        return err
    dest = data_dir() / CUSTOM_HORN
    tmp = dest.with_suffix(".tmp")
    try:
        shutil.copyfile(src, tmp)
        os.replace(tmp, dest)
    except OSError as exc:
        log.exception("Could not install custom horn")
        return f"Could not copy the file: {exc}"
    return None


def remove_custom_horn() -> None:
    try:
        (data_dir() / CUSTOM_HORN).unlink()
    except FileNotFoundError:
        pass


def has_custom_horn() -> bool:
    return validate_wav(data_dir() / CUSTOM_HORN) is None


def horn_path() -> Optional[Path]:
    custom = data_dir() / CUSTOM_HORN
    if custom.is_file() and validate_wav(custom) is None:
        return custom
    return _ensure(HORN_FILE, synth_horn_samples, 0.89)


_volume = 80                 # 0-100, set by the app from settings
_scale_lock = threading.Lock()


def _apply_hardware_volume(volume: int) -> bool:
    """Modulate process audio volume via Windows Multimedia API (0-100) in real time."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        level = max(0, min(100, int(volume)))
        # Square the perceptual gain curve for hardware attenuation
        gain = (level / 100.0) ** 2
        raw = int(round(gain * 0xFFFF))
        dw = (raw & 0xFFFF) | ((raw & 0xFFFF) << 16)
        return ctypes.windll.winmm.waveOutSetVolume(0, dw) == 0
    except Exception:
        return False


def set_volume(volume: int) -> None:
    global _volume
    _volume = max(0, min(100, int(volume)))
    _apply_hardware_volume(_volume)


def scaled_copy(path: Path, volume: int) -> Optional[Path]:
    """Return a cached copy of ``path`` at ``volume`` percent (None = muted).

    ``winsound`` has no volume control, so the samples themselves are scaled
    with a perceptual (squared) curve and written to the app data folder.
    """
    if volume <= 0:
        return None
    if volume >= 100:
        return path
    out = data_dir() / f"_play_{path.stem}_{volume}.wav"
    with _scale_lock:
        if out.is_file() and out.stat().st_mtime >= path.stat().st_mtime:
            return out
        try:
            with wave.open(str(path), "rb") as r:
                params, frames = r.getparams(), r.readframes(r.getnframes())
            gain = (volume / 100.0) ** 2
            if params.sampwidth == 2:
                pcm = array("h")
                pcm.frombytes(frames)
                if sys.byteorder == "big":
                    pcm.byteswap()
                pcm = array("h", (int(x * gain) for x in pcm))
                if sys.byteorder == "big":
                    pcm.byteswap()
                frames = pcm.tobytes()
            elif params.sampwidth == 1:
                frames = bytes(int((b - 128) * gain) + 128 for b in frames)
            else:
                return path
            tmp = out.with_suffix(".tmp")
            with wave.open(str(tmp), "wb") as w:
                w.setparams(params)
                w.writeframes(frames)
            os.replace(tmp, out)
        except (OSError, wave.Error, EOFError):
            log.exception("Could not scale %s", path.name)
            return path
        for old in data_dir().glob(f"_play_{path.stem}_*.wav"):   # keep only the current level
            if old != out:
                try:
                    old.unlink()
                except OSError:
                    pass
    return out


def prepare_volume(volume: int) -> None:
    """Pre-render scaled sounds (background thread) so playback is instant."""
    for p in (horn_path(), _ensure(CHIME_FILE, synth_chime_samples, 0.45)):
        if p:
            scaled_copy(p, volume)


def _play(path: Optional[Path]) -> None:
    try:
        import winsound
    except ImportError:  # non-Windows
        return
    if not path or _volume <= 0:
        return
    hw_ok = _apply_hardware_volume(_volume)
    target = path if hw_ok else scaled_copy(path, _volume)
    if target is None:          # volume 0 = silent
        return
    try:
        winsound.PlaySound(str(target), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
    except RuntimeError:
        log.exception("Sound playback failed")


def play_horn() -> None:
    _play(horn_path())


def play_chime() -> None:
    _play(_ensure(CHIME_FILE, synth_chime_samples, 0.45))
