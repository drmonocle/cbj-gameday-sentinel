"""Tests for v1.1 features: news sources, live situation, standings, settings, assets."""
import json
import wave

import pytest

from cbj_sentinel import assets, config, data, net, settings


# ---------------------------------------------------------------- news
ATOM = b"""<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Game Thread: CBJ vs PIT</title><link href="https://www.reddit.com/r/BlueJackets/comments/abc/"/>
<updated>2026-10-05T23:00:00+00:00</updated></entry></feed>"""


def test_parse_atom_feed():
    items = data.parse_feed(ATOM, "r/BlueJackets")
    assert items[0]["title"] == "Game Thread: CBJ vs PIT"
    assert items[0]["link"].startswith("https://www.reddit.com/")
    assert items[0]["source"] == "r/BlueJackets" and items[0]["ts"] > 0


def test_parse_forge_validates_slug():
    raw = {"items": [{"headline": "Good", "slug": "cbj-win-recap", "contentDate": "2026-10-05T12:00:00Z"},
                     {"headline": "Bad", "slug": "../../evil?x=1"}]}
    items = data.parse_forge(raw)
    assert [i["title"] for i in items] == ["Good"]
    assert items[0]["link"] == "https://www.nhl.com/news/cbj-win-recap"


def test_parse_espn_upgrades_http():
    raw = {"articles": [{"headline": "H", "description": "D", "published": "2026-10-05T12:00:00Z",
                         "links": {"web": {"href": "http://www.espn.com/nhl/story/_/id/1"}}}]}
    assert data.parse_espn(raw)[0]["link"] == "https://www.espn.com/nhl/story/_/id/1"


def test_merge_news_sorts_and_dedupes():
    a = [{"title": "Same story", "ts": 10, "source": "A", "link": "", "desc": ""}]
    b = [{"title": "same STORY", "ts": 5, "source": "B", "link": "", "desc": ""},
         {"title": "Newest", "ts": 20, "source": "B", "link": "", "desc": ""}]
    merged = data.merge_news(a, b)
    assert [i["title"] for i in merged] == ["Newest", "Same story"]


def test_ago():
    assert data.ago(1000, now=1000 + 7200) == "2h ago"
    assert data.ago(0) == ""


# ---------------------------------------------------------------- live game
def live(code, home="CBJ", away="PIT"):
    return {"homeTeam": {"abbrev": home}, "awayTeam": {"abbrev": away},
            "situation": {"situationCode": code, "timeRemaining": "1:23"}}


@pytest.mark.parametrize("code,pp,en,adv", [
    ("1551", None, [], "5-on-5"),
    ("1451", "CBJ", [], "5-on-4"),      # home (CBJ) power play
    ("1541", "PIT", [], "5-on-4"),
    ("1560", None, ["CBJ"], "6-on-5"),  # CBJ (home) pulled the goalie: not a PP
    ("0641", "PIT", ["PIT"], "6-on-4"), # PIT on a PP *and* pulled their goalie
])
def test_situation_codes(code, pp, en, adv):
    s = data.situation(live(code))
    assert s["pp"] == pp and s["empty_net"] == en and s["advantage"] == adv


def test_situation_ignores_garbage():
    assert data.situation(live("abc"), {"situation": {"situationCode": "12"}}) == {}
    assert data.situation(None) == {}


def test_enrich_keeps_live_scores_and_adds_names():
    sched = {"id": 1, "venue": {"default": "Nationwide Arena"},
             "homeTeam": {"abbrev": "CBJ", "placeName": {"default": "Columbus"}, "commonName": {"default": "Blue Jackets"}},
             "awayTeam": {"abbrev": "PIT", "placeName": {"default": "Pittsburgh"}, "commonName": {"default": "Penguins"}}}
    now = {"id": 1, "gameState": "LIVE", "homeTeam": {"abbrev": "CBJ", "score": 2}, "awayTeam": {"abbrev": "PIT", "score": 1}}
    g = data.enrich(now, sched)
    assert g["homeTeam"]["score"] == 2 and g["gameState"] == "LIVE"
    assert data.matchup_line(g, "CBJ") == "vs Pittsburgh Penguins"
    assert data.venue_line(g) == "Nationwide Arena \u00b7 Columbus"


def test_team_name_fallback():
    assert data.matchup_line({"homeTeam": {"abbrev": "BUF"}, "awayTeam": {"abbrev": "CBJ"}}, "CBJ") == "@ Buffalo Sabres"


def test_broadcasts_filters_market():
    g = {"homeTeam": {"abbrev": "CBJ"}, "awayTeam": {"abbrev": "PIT"}, "tvBroadcasts": [
        {"countryCode": "US", "market": "H", "network": "CBJHN"},
        {"countryCode": "US", "market": "A", "network": "SN-PIT"},
        {"countryCode": "CA", "market": "N", "network": "SN+"},
        {"countryCode": "US", "market": "N", "network": "TNT"}]}
    assert data.broadcasts(g, "CBJ") == "CBJHN, TNT"
    assert data.broadcasts(g) == "CBJHN, SN-PIT, TNT"


def test_penalty_lines():
    landing = {"summary": {"penalties": [{"periodDescriptor": {"number": 1, "periodType": "REG"}, "penalties": [
        {"timeInPeriod": "04:12", "duration": 2, "descKey": "high-sticking", "teamAbbrev": {"default": "PIT"},
         "committedByPlayer": {"firstName": {"default": "Sidney"}, "lastName": {"default": "Crosby"}}}]}]}}
    assert data.penalty_lines(landing) == ["1st 04:12  [PIT] Sidney Crosby \u2013 high sticking (2 min)"]


def test_last_scorer():
    goals = [{"teamAbbrev": "CBJ", "name": {"default": "Z. Werenski"}}, {"teamAbbrev": {"default": "PIT"}, "name": "X"}]
    assert data.last_scorer(goals, "CBJ") == "Z. Werenski"


# ---------------------------------------------------------------- standings
def team(ab, div, seq, wc=0, conf="E"):
    return {"teamAbbrev": {"default": ab}, "divisionAbbrev": div, "conferenceAbbrev": conf,
            "divisionSequence": seq, "wildcardSequence": wc, "points": 10}


def test_standings_tables():
    rows = [team("CBJ", "M", 2), team("PIT", "M", 1), team("NYR", "M", 4, wc=2), team("BOS", "A", 1),
            team("BUF", "A", 5, wc=1), team("DAL", "C", 1, conf="W")]
    t = data.standings_tables({"standings": rows}, "M", "E")
    assert [data.name_of(r["teamAbbrev"]) for r in t["division"]] == ["PIT", "CBJ", "NYR"]
    assert [data.name_of(r["teamAbbrev"]) for r in t["wildcard"]] == ["BUF", "NYR"]
    assert "DAL" not in [data.name_of(r["teamAbbrev"]) for r in t["leaders"]]


def test_version_tuple():
    assert data.version_tuple("v1.10.0") > data.version_tuple("1.9.9")
    assert data.version_tuple("garbage") == (0,)


# ---------------------------------------------------------------- settings
def test_settings_sanitize_rejects_wrong_types_and_clamps():
    s = settings.sanitize({"sound": 1, "delay_seconds": True, "watch": "evil", "overlay_x": 999999,
                           "spoiler_mode": True, "unknown": "x"})
    assert s["sound"] is True                      # 1 is not a bool -> default kept
    assert s["delay_seconds"] == 0                 # True is not an int -> default kept
    assert s["watch"] == "prime"
    assert s["overlay_x"] == 20000
    assert s["spoiler_mode"] is True
    assert "unknown" not in s
    assert settings.sanitize({"delay_seconds": 999})["delay_seconds"] == 180
    assert settings.sanitize("not a dict") == settings.DEFAULTS


def test_settings_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    s = dict(settings.DEFAULTS, watch="espn", delay_seconds=45)
    settings.save(s)
    assert settings.load()["watch"] == "espn"
    (tmp_path / config.APP_ID / "settings.json").write_text("{broken", encoding="utf-8")
    assert settings.load() == settings.DEFAULTS


# ---------------------------------------------------------------- allowlists
@pytest.mark.parametrize("key", list(config.WATCH_OPTIONS))
def test_watch_options_are_openable(key):
    assert net.is_safe_browser_url(config.WATCH_OPTIONS[key][1])


def test_prime_and_lookalikes():
    assert net.is_safe_browser_url("https://www.amazon.com/gp/video/channel/19bfae52-c58d-83c8-3909-2f61654f1afb")
    assert not net.is_safe_browser_url("https://www.amazon.com.evil.com/gp/video")
    assert not net.is_safe_browser_url("https://amazon.co/")


def test_news_sources_are_fetchable_hosts():
    for src in config.NEWS_SOURCES:
        net.validate_url(src["url"], config.FETCH_HOSTS)


# ---------------------------------------------------------------- assets
def _wav(path, seconds, rate=8000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(seconds * rate))


def test_custom_horn_validation(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    good, long_, junk = tmp_path / "g.wav", tmp_path / "l.wav", tmp_path / "j.wav"
    _wav(good, 2)
    _wav(long_, config.MAX_CUSTOM_WAV_SECONDS + 1)
    junk.write_bytes(b"MZ\x90\x00 not a wav")
    assert assets.validate_wav(good) is None
    assert "longer" in assets.validate_wav(long_)
    assert assets.validate_wav(junk)
    assert assets.install_custom_horn(junk)
    assert not assets.has_custom_horn()
    assert assets.install_custom_horn(good) is None
    assert assets.has_custom_horn()
    assert assets.horn_path().name == assets.CUSTOM_HORN
    assets.remove_custom_horn()
    assert not assets.has_custom_horn()


def test_safe_image_rejects_non_images():
    with pytest.raises(Exception):
        assets.load_safe_image(b"<svg xmlns='http://www.w3.org/2000/svg'/>", 64)


def test_score_icon():
    assert assets.score_icon(10, 2).size == (64, 64)
