"""Tests for CBJ Gameday Sentinel v1.4.0 features:
- Regulation Ice Rink & Shot Chart coordinate parsing
- 32-team NHL preset catalog & dynamic config
- Compact Floating Ticker Bar settings & data structures
"""
import math
import re
from typing import Any, Dict

import pytest

from cbj_sentinel import config as C, data, settings


# ---------------------------------------------------------------- shot chart
def test_parse_shot_chart_empty():
    res = data.parse_shot_chart({})
    assert res["shots"] == []
    assert res["counts"]["target_sog"] == 0
    assert res["counts"]["total_shots"] == 0
    assert res["opponent"] == "OPP"


def test_parse_shot_chart_coordinates_normalization():
    pbp = {
        "id": 2026020027,
        "homeTeam": {"id": 29, "abbrev": "CBJ"},
        "awayTeam": {"id": 68, "abbrev": "UTA"},
        "rosterSpots": [
            {"playerId": 101, "firstName": {"default": "Kirill"}, "lastName": {"default": "Marchenko"}},
            {"playerId": 202, "firstName": {"default": "Clayton"}, "lastName": {"default": "Keller"}},
        ],
        "plays": [
            # Shot from offensive zone right side at right net (x=73, y=7)
            {
                "eventId": 1,
                "typeDescKey": "shot-on-goal",
                "periodDescriptor": {"number": 1},
                "timeInPeriod": "05:20",
                "details": {
                    "xCoord": 73,
                    "yCoord": 7,
                    "shotType": "wrist",
                    "shootingPlayerId": 101,
                    "eventOwnerTeamId": 29,
                }
            },
            # Goal from left net normalized (x=-82, y=-4) -> nx=82, ny=4
            {
                "eventId": 2,
                "typeDescKey": "goal",
                "periodDescriptor": {"number": 2},
                "timeInPeriod": "14:10",
                "details": {
                    "xCoord": -82,
                    "yCoord": -4,
                    "shotType": "backhand",
                    "scoringPlayerId": 202,
                    "eventOwnerTeamId": 68,
                }
            },
            # Play without coordinates (faceoff, hit, etc.) -> should be ignored
            {
                "eventId": 3,
                "typeDescKey": "faceoff",
                "details": {"xCoord": 0, "yCoord": 0}
            }
        ]
    }

    res = data.parse_shot_chart(pbp, team_id=29, team_abbrev="CBJ")
    assert res["game_id"] == 2026020027
    assert res["opponent"] == "UTA"
    assert len(res["shots"]) == 2

    # Shot 1: CBJ
    s1 = res["shots"][0]
    assert s1["is_cbj"] is True
    assert s1["player"] == "Kirill Marchenko"
    assert s1["x"] == 73.0
    assert s1["y"] == 7.0
    assert s1["dist"] == round(math.sqrt((89 - 73)**2 + 7**2), 1)
    assert s1["shotType"] == "wrist"

    # Shot 2: Opponent Goal (normalized from negative x)
    s2 = res["shots"][1]
    assert s2["is_cbj"] is False
    assert s2["player"] == "Clayton Keller"
    assert s2["x"] == 82.0
    assert s2["y"] == 4.0
    assert s2["dist"] == round(math.sqrt((89 - 82)**2 + 4**2), 1)
    assert s2["type"] == "goal"

    # Counts
    counts = res["counts"]
    assert counts["target_sog"] == 1
    assert counts["target_goals"] == 0
    assert counts["opp_sog"] == 1
    assert counts["opp_goals"] == 1
    assert counts["total_shots"] == 2


# ---------------------------------------------------------------- 32-team presets
def test_team_presets_full_32_nhl_roster():
    presets = C.TEAM_PRESETS
    assert len(presets) == 32, f"Expected 32 NHL teams, got {len(presets)}"

    hex_re = re.compile(r"^#[0-9A-Fa-f]{6}$")
    valid_divisions = {"M", "A", "C", "P"}
    valid_conferences = {"E", "W"}

    for tricode, p in presets.items():
        assert len(tricode) == 3, f"Invalid tricode {tricode}"
        assert p["division"] in valid_divisions, f"{tricode} invalid division {p['division']}"
        assert p["conference"] in valid_conferences, f"{tricode} invalid conference {p['conference']}"
        assert isinstance(p["nhl_id"], int) and p["nhl_id"] > 0
        assert isinstance(p["espn_id"], int) and p["espn_id"] > 0
        assert hex_re.match(p["primary"]), f"{tricode} invalid primary color {p['primary']}"
        assert hex_re.match(p["secondary"]), f"{tricode} invalid secondary color {p['secondary']}"
        assert len(p["subreddit"]) > 0


def test_active_team_defaults_to_cbj():
    assert C.TEAM == "CBJ"
    assert C.NHL_TEAM_ID == 29
    assert C.ESPN_TEAM_ID == 29
    assert C.TEAM_DIVISION == "M"
    assert C.TEAM_CONFERENCE == "E"
    assert "cbj.png" in C.LOGO_URL


# ---------------------------------------------------------------- settings
def test_ticker_settings_sanitized():
    s = settings.sanitize({
        "ticker_bar": True,
        "ticker_x": 500,
        "ticker_y": 300,
    })
    assert s["ticker_bar"] is True
    assert s["ticker_x"] == 500
    assert s["ticker_y"] == 300


def test_ticker_settings_limits():
    s = settings.sanitize({
        "ticker_x": -999,
        "ticker_y": 999999,
    })
    assert s["ticker_x"] == -1      # clamped to lo=-1
    assert s["ticker_y"] == 20000   # clamped to hi=20000
