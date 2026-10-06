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
    assert s1["game_date"] == ""
    assert s2["opponent"] == "UTA"


def test_combine_shot_charts_multi_game():
    c1 = {
        "game_id": 1,
        "counts": {"target_sog": 20, "target_goals": 2, "opp_sog": 30, "opp_goals": 3, "total_shots": 70},
        "shots": [
            {"id": 1, "type": "goal", "is_cbj": True, "x": 75, "y": 0, "dist": 14},
            {"id": 2, "type": "shot-on-goal", "is_cbj": True, "x": 50, "y": 10, "dist": 40},
            {"id": 3, "type": "goal", "is_cbj": False, "x": 80, "y": 5, "dist": 10},
        ]
    }
    c2 = {
        "game_id": 2,
        "counts": {"target_sog": 25, "target_goals": 3, "opp_sog": 25, "opp_goals": 1, "total_shots": 65},
        "shots": [
            {"id": 4, "type": "goal", "is_cbj": True, "x": 70, "y": -5, "dist": 20},
            {"id": 5, "type": "shot-on-goal", "is_cbj": False, "x": 45, "y": 0, "dist": 44},
        ]
    }

    combined = data.combine_shot_charts([c1, c2], target_abbrev="CBJ")
    assert combined["game_id"] == "combined"
    assert combined["games_count"] == 2
    assert len(combined["shots"]) == 5
    assert combined["counts"]["target_sog"] == 45
    assert combined["counts"]["target_goals"] == 5
    assert combined["counts"]["opp_sog"] == 55
    assert combined["counts"]["opp_goals"] == 4
    assert combined["counts"]["total_shots"] == 5
    assert combined["counts"]["target_sh_pct"] == round(5 / 45 * 100, 1)
    assert combined["counts"]["opp_sh_pct"] == round(4 / 55 * 100, 1)


def test_shot_chart_independent_filters():
    from cbj_sentinel import rink
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    sc = rink.ShotChart(root)

    test_payload = {
        "game_id": 2026020027,
        "matchup": "UTA @ CBJ",
        "game_date": "2026-10-03",
        "target_score": 1,
        "opp_score": 4,
        "counts": {"target_sog": 19, "target_goals": 1, "opp_sog": 31, "opp_goals": 4, "total_shots": 5},
        "shots": [
            {"id": 1, "type": "goal", "is_cbj": False, "period": 1, "player": "Sergachev", "shotType": "slap"},
            {"id": 2, "type": "goal", "is_cbj": False, "period": 1, "player": "Schmaltz", "shotType": "snap"},
            {"id": 3, "type": "goal", "is_cbj": True, "period": 2, "player": "Johnson", "shotType": "snap"},
            {"id": 4, "type": "goal", "is_cbj": False, "period": 3, "player": "Guenther", "shotType": "slap"},
            {"id": 5, "type": "goal", "is_cbj": False, "period": 3, "player": "Schmaltz", "shotType": "wrist"},
        ]
    }
    sc.load_shots(test_payload)

    # By default: filter_team="all", filter_type="all" -> all 5 shots visible (each goal has halo, star, text)
    displayed_shots = set(s["id"] for s in sc._marker_items.values())
    assert len(displayed_shots) == 5

    # Filter: CBJ Only ("target") + Goals ("goals") -> only Kent Johnson (1 goal)
    sc._set_team_filter("target")
    sc._set_type_filter("goals")
    displayed_shots = set(s["id"] for s in sc._marker_items.values())
    assert len(displayed_shots) == 1
    assert "Showing 1 CBJ Goal" in sc.l_filter_status.cget("text")

    # Filter: Both Teams ("all") + Goals ("goals") -> all 5 goals
    sc._set_team_filter("all")
    sc._set_type_filter("goals")
    displayed_shots = set(s["id"] for s in sc._marker_items.values())
    assert len(displayed_shots) == 5
    assert "Showing 5 Total Goals" in sc.l_filter_status.cget("text")

    # Filter: Opponent Only ("opp") + Goals ("goals") -> 4 goals
    sc._set_team_filter("opp")
    displayed_shots = set(s["id"] for s in sc._marker_items.values())
    assert len(displayed_shots) == 4
    assert "Showing 4 Opponent Goals" in sc.l_filter_status.cget("text")

    root.destroy()


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
