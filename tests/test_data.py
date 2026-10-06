import pytest

from cbj_sentinel import data


def game(gid, home, hs, away, as_, gtype=2, state="OFF", last="REG"):
    return {"id": gid, "gameType": gtype, "gameState": state,
            "homeTeam": {"abbrev": home, "score": hs}, "awayTeam": {"abbrev": away, "score": as_},
            "gameOutcome": {"lastPeriodType": last}}


SCHEDULE = [
    game(1, "CBJ", 1, "DET", 0, gtype=1),
    game(2, "BUF", 5, "CBJ", 1, gtype=1),
    game(3, "CBJ", 6, "BUF", 3),
    game(4, "CBJ", 1, "UTA", 4),
    game(5, "PIT", 3, "CBJ", 2, last="OT"),
    game(6, "CBJ", 0, "PIT", 0, state="FUT"),
]


def test_record_separates_game_types():
    reg = data.team_record(SCHEDULE, "CBJ", 2)
    pre = data.team_record(SCHEDULE, "CBJ", 1)
    assert (reg["w"], reg["l"], reg["otl"], reg["gf"], reg["ga"]) == (1, 1, 1, 9, 10)
    assert (pre["w"], pre["l"], pre["gp"]) == (1, 1, 2)


def test_goal_tracker_resets_between_games():
    t = data.GoalTracker()
    assert t.update(100, 2) is False      # app opened mid-game: baseline, no horn
    assert t.update(100, 3) is True       # goal
    assert t.update(100, 3) is False
    assert t.update(100, 2) is False      # goal overturned
    assert t.update(200, 0) is False      # next night, new game
    assert t.update(200, 1) is True       # horn fires again (old bug: it didn't)


def test_countdown_formats():
    assert data.format_countdown(3 * 86400 + 5 * 3600 + 12 * 60) == "3d 05h 12m"
    assert data.format_countdown(3725) == "01h 02m 05s"
    assert data.format_countdown(-5) == "00h 00m 00s"


def test_period_labels():
    assert data.period_label({"periodDescriptor": {"number": 2, "periodType": "REG"}}) == "2nd"
    assert data.period_label({"periodDescriptor": {"number": 4, "periodType": "OT"}}) == "OT"
    assert data.period_label({"periodDescriptor": {"number": 6, "periodType": "OT"}}) == "3OT"
    assert data.period_label({"periodDescriptor": {"number": 5, "periodType": "SO"}}) == "Shootout"


def test_clean_text_strips_markup_and_controls():
    assert data.clean_text("<p>Hi &amp; <b>bye</b>\x07</p>") == "Hi & bye"
    assert data.clean_text("x" * 50, 10).endswith("\u2026")


GOOD_FEED = b"""<?xml version="1.0"?><rss><channel>
<item><title>Big &amp;amp; Win</title><link>https://www.1stohiobattery.com/a</link>
<pubDate>Wed, 30 Sep 2026 12:00:00 GMT</pubDate><description>&lt;p&gt;Recap&lt;/p&gt;</description></item>
</channel></rss>"""


def test_parse_feed_ok():
    items = data.parse_feed(GOOD_FEED)
    assert items[0]["title"] == "Big & Win"
    assert items[0]["desc"] == "Recap"
    assert items[0]["link"] == "https://www.1stohiobattery.com/a"


def test_parse_feed_rejects_entity_expansion():
    bomb = b"""<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;">]>
<rss><channel><item><title>&lol2;</title></item></channel></rss>"""
    with pytest.raises(ValueError):
        data.parse_feed(bomb)


def test_parse_feed_rejects_html():
    with pytest.raises(ValueError):
        data.parse_feed(b"<html><body>Not a feed</body></html>")


def test_goal_lines_handles_string_and_dict_fields():
    lines = data.goal_lines([
        {"periodDescriptor": {"number": 1, "periodType": "REG"}, "timeInPeriod": "12:51",
         "teamAbbrev": "CBJ", "firstName": {"default": "Cole"}, "lastName": {"default": "Sillinger"},
         "strength": "pp"},
        {"period": 4, "periodDescriptor": {"number": 4, "periodType": "OT"}, "timeInPeriod": "01:00",
         "teamAbbrev": {"default": "CBJ"}, "name": {"default": "A. Fantilli"}},
    ])
    assert lines[0] == "P1 12:51  [CBJ] Cole Sillinger (PPG)"
    assert lines[1] == "OT 01:00  [CBJ] A. Fantilli"
