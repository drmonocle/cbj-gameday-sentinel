"""Regression tests for the audit fixes (shot-chart geometry, filtering, versions)."""
import re
from pathlib import Path

from cbj_sentinel import __version__, config as C, data

ROOT = Path(__file__).resolve().parent.parent


def _pbp(plays, side="right"):
    for p in plays:
        p.setdefault("homeTeamDefendingSide", side)
        p.setdefault("periodDescriptor", {"number": 1, "periodType": "REG"})
    return {"id": 1, "homeTeam": {"id": 29, "abbrev": "CBJ"}, "awayTeam": {"id": 59, "abbrev": "UTA"},
            "plays": plays}


def _shot(x, y, owner, type_key="shot-on-goal"):
    return {"typeDescKey": type_key, "details": {"xCoord": x, "yCoord": y, "eventOwnerTeamId": owner}}


def test_orientation_uses_defending_side_for_both_teams():
    # Home (CBJ) defends the right net, so attacks x=-89; the visitor attacks x=+89.
    res = data.parse_shot_chart(_pbp([_shot(-70, 5, 29), _shot(60, -8, 59)]), 29, "CBJ")
    cbj, opp = res["shots"]
    assert (cbj["x"], cbj["y"], cbj["is_cbj"]) == (70.0, -5.0, True)
    assert (opp["x"], opp["y"], opp["is_cbj"]) == (60.0, -8.0, False)


def test_shot_from_own_half_is_not_mirrored_into_offensive_zone():
    # CBJ attacks left; a shot from x=+40 is from its own half. abs(x) used to turn it into a 49 ft shot.
    res = data.parse_shot_chart(_pbp([_shot(40, 0, 29)]), 29, "CBJ")
    s = res["shots"][0]
    assert s["x"] == -40.0
    assert s["dist"] == 129.0


def test_orientation_flips_with_period_side():
    plays = [_shot(70, 5, 29)]
    plays[0]["homeTeamDefendingSide"] = "left"   # CBJ now attacks right
    assert data.parse_shot_chart(_pbp(plays), 29, "CBJ")["shots"][0]["x"] == 70.0


def test_falls_back_to_sign_of_x_without_defending_side():
    pbp = _pbp([_shot(-82, -4, 59)])
    del pbp["plays"][0]["homeTeamDefendingSide"]
    s = data.parse_shot_chart(pbp, 29, "CBJ")["shots"][0]
    assert (s["x"], s["y"]) == (82.0, 4.0)


def test_shootout_attempts_are_excluded():
    so = _shot(80, 0, 29, "goal")
    so["periodDescriptor"] = {"number": 5, "periodType": "SO"}
    res = data.parse_shot_chart(_pbp([so, _shot(-70, 0, 29)]), 29, "CBJ")
    assert len(res["shots"]) == 1
    assert res["counts"]["target_goals"] == 0


def test_shot_chart_games_excludes_preseason():
    games = [{"id": 1, "gameType": 1}, {"id": 2, "gameType": 2}, {"id": 3, "gameType": 3}, {"id": 4}]
    assert [g["id"] for g in data.shot_chart_games(games)] == [2, 3]


def test_versions_are_in_sync():
    assert re.search(rf'^version = "{re.escape(__version__)}"$', (ROOT / "pyproject.toml").read_text(), re.M)
    info = (ROOT / "version_info.txt").read_text()
    assert f"'FileVersion', '{__version__}.0'" in info
    assert f"'ProductVersion', '{__version__}.0'" in info


def test_every_team_config_is_self_consistent():
    import importlib
    import os
    from cbj_sentinel import settings
    original = os.environ.get("NHL_SENTINEL_TEAM")
    try:
        for code in C.TEAM_PRESETS:
            os.environ["NHL_SENTINEL_TEAM"] = code
            cfg = importlib.reload(C)
            assert cfg.TEAM == code
            assert cfg.DEFAULT_WATCH in cfg.WATCH_OPTIONS
            assert importlib.reload(settings).DEFAULTS["watch"] == cfg.DEFAULT_WATCH
            assert cfg.LOGO_URL.endswith(".png") and f"/{code.lower()}.png" in cfg.LOGO_URL or code in ("NJD", "TBL", "SJS", "LAK")
            assert ("prime" in cfg.WATCH_OPTIONS) == (code == "CBJ")
            # news sources only reference the CBJ-only feeds for CBJ
            ids = {s["id"] for s in cfg.NEWS_SOURCES}
            assert ("cannon" in ids) == (code == "CBJ")
    finally:
        if original is None:
            os.environ.pop("NHL_SENTINEL_TEAM", None)
        else:
            os.environ["NHL_SENTINEL_TEAM"] = original
        importlib.reload(C)
        importlib.reload(settings)


def test_espn_and_nhl_ids_are_unique():
    for field in ("nhl_id", "espn_id"):
        values = [p[field] for p in C.TEAM_PRESETS.values()]
        assert len(values) == len(set(values)), field
