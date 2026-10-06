"""Tests for v1.2 fixes: 1st Ohio Battery dates, per-source news, records, volume, logo."""
import io
import wave
from array import array

import pytest
from PIL import Image

from cbj_sentinel import assets, config, data, settings

OB_FEED = b"""<?xml version="1.0" encoding="utf-8" ?><rss version="2.0"><channel>
<item><title>Marchenko trade</title><link>https://www.1stohiobattery.com/a</link>
<pubDate>Wednesday, September 30, 2026 - 15:15</pubDate></item></channel></rss>"""


def test_drupal_pubdate_parses():
    item = data.parse_feed(OB_FEED, "1st Ohio Battery")[0]
    assert item["ts"] > 0 and data.ago(item["ts"]) != ""


def test_merge_news_never_crowds_out_a_source():
    busy = [{"title": f"busy {i}", "ts": 1000 + i, "source": "Reddit", "link": "", "desc": ""} for i in range(100)]
    slow = [{"title": "old 1OB story", "ts": 1, "source": "1st Ohio Battery", "link": "", "desc": ""}]
    merged = data.merge_news(busy, slow)
    assert any(i["source"] == "1st Ohio Battery" for i in merged)
    assert sum(i["source"] == "Reddit" for i in merged) == 15


def test_record_counts_shootout_win_as_one_goal():
    g = {"gameType": 1, "gameState": "FINAL", "homeTeam": {"abbrev": "CBJ", "score": 1},
         "awayTeam": {"abbrev": "DET", "score": 0}, "gameOutcome": {"lastPeriodType": "SO"}}
    loss = {"gameType": 1, "gameState": "OFF", "homeTeam": {"abbrev": "BUF", "score": 3},
            "awayTeam": {"abbrev": "CBJ", "score": 2}, "gameOutcome": {"lastPeriodType": "OT"}}
    rec = data.team_record([g, loss], "CBJ", 1)
    assert (rec["w"], rec["l"], rec["otl"], rec["gf"], rec["ga"]) == (1, 0, 1, 3, 3)


def _wav(path, width=2, rate=8000, seconds=0.5, value=10000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(width)
        w.setframerate(rate)
        n = int(rate * seconds)
        if width == 2:
            w.writeframes(array("h", [value] * n).tobytes())
        else:
            w.writeframes(b"\x00" * n * width)


def test_volume_scaling(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    src = tmp_path / "h.wav"
    _wav(src)
    assert assets.scaled_copy(src, 0) is None          # muted
    assert assets.scaled_copy(src, 100) == src         # untouched
    out = assets.scaled_copy(src, 50)
    with wave.open(str(out), "rb") as r:
        pcm = array("h")
        pcm.frombytes(r.readframes(r.getnframes()))
    assert pcm[0] == int(10000 * 0.25)                 # perceptual curve: 50% -> 0.25 gain
    out2 = assets.scaled_copy(src, 30)
    assert out2.exists() and not out.exists()          # old level cleaned up


def test_24bit_custom_horn_rejected(tmp_path):
    p = tmp_path / "x.wav"
    _wav(p, width=3)
    assert assets.validate_wav(p)


def test_volume_setting_clamped():
    assert settings.sanitize({"volume": 250})["volume"] == 100
    assert settings.sanitize({"volume": True})["volume"] == 80


def test_team_logo_is_validated_and_cached(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assets._logo_cache.clear()
    assert assets.team_logo_stale()
    buf = io.BytesIO()
    Image.new("RGBA", (200, 200), (200, 16, 46, 255)).save(buf, format="PNG")
    assets.save_team_logo(buf.getvalue())
    assert not assets.team_logo_stale()
    icon = assets.app_icon(32)
    assert icon.size == (32, 32) and icon.getpixel((16, 16))[0] > 150   # uses the logo, not the star
    with pytest.raises(Exception):
        assets.save_team_logo(b"<html>not an image</html>")
    assets._logo_cache.clear()


def test_logo_host_allowlisted():
    from cbj_sentinel import net
    net.validate_url(config.LOGO_URL, config.FETCH_HOSTS)


def test_hardware_volume_modulation():
    assets.set_volume(45)
    assert assets._volume == 45
    assets.set_volume(0)
    assert assets._volume == 0
    assets.set_volume(150)
    assert assets._volume == 100
    assets.set_volume(80)
