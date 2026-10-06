"""Pure data helpers (no UI, no network) so they can be unit tested."""
from __future__ import annotations

import html
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple

FINAL_STATES = ("FINAL", "OFF")
LIVE_STATES = ("LIVE", "CRIT")
GAME_TYPES = {1: "Preseason", 2: "Regular Season", 3: "Playoffs"}

_TAG_RE = re.compile(r"<[^>]+>")
_CTRL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_WS_RE = re.compile(r"\s+")


# ---------------------------------------------------------------- text utils
def name_of(value: Any) -> str:
    """NHL API fields are either {'default': 'X'} or plain strings."""
    if isinstance(value, dict):
        value = value.get("default", "")
    return str(value) if value is not None else ""


def clean_text(value: Any, max_len: int = 400) -> str:
    """Unescape HTML, strip tags/control chars, collapse whitespace, truncate."""
    text = html.unescape(str(value or ""))
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)  # feeds often double-encode
    text = _CTRL_RE.sub("", text)
    text = _WS_RE.sub(" ", text).strip()
    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "\u2026"
    return text


# ---------------------------------------------------------------- time utils
def parse_utc(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def format_countdown(seconds: float) -> str:
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days:
        return f"{days}d {hours:02d}h {minutes:02d}m"
    return f"{hours:02d}h {minutes:02d}m {secs:02d}s"


def local_start(game: Dict[str, Any]) -> str:
    """e.g. 'Fri Oct 9 \u00b7 7:00 PM' in the user's local timezone."""
    dt = parse_utc(game.get("startTimeUTC"))
    if not dt:
        return game.get("gameDate", "")
    local = dt.astimezone()
    return f"{local:%a %b} {local.day} \u00b7 {local:%I:%M %p}".replace(" 0", " ")


# ---------------------------------------------------------------- game utils
def perspective(game: Dict[str, Any], team: str) -> Tuple[bool, dict, dict]:
    """Return (is_home, our_team, their_team)."""
    home, away = game.get("homeTeam") or {}, game.get("awayTeam") or {}
    is_home = home.get("abbrev") == team
    return is_home, (home if is_home else away), (away if is_home else home)


def involves(game: Dict[str, Any], team: str) -> bool:
    return team in ((game.get("homeTeam") or {}).get("abbrev"),
                    (game.get("awayTeam") or {}).get("abbrev"))


def find_team_game(score_data: Dict[str, Any], team: str) -> Optional[dict]:
    for game in score_data.get("games", []) or []:
        if involves(game, team):
            return game
    return None


def split_schedule(games: List[dict]) -> Tuple[List[dict], List[dict]]:
    past = [g for g in games if g.get("gameState") in FINAL_STATES]
    upcoming = [g for g in games if g.get("gameState") not in FINAL_STATES]
    return past, upcoming


def result_of(game: Dict[str, Any], team: str) -> Tuple[str, int, int]:
    """('W'|'L'|'OTL', our_score, their_score) for a final game."""
    _, us, them = perspective(game, team)
    ours, theirs = int(us.get("score") or 0), int(them.get("score") or 0)
    if ours > theirs:
        return "W", ours, theirs
    last = (game.get("gameOutcome") or {}).get("lastPeriodType", "REG")
    return ("OTL" if last in ("OT", "SO") else "L"), ours, theirs


def team_record(games: List[dict], team: str, game_type: int) -> Dict[str, int]:
    rec = {"gp": 0, "w": 0, "l": 0, "otl": 0, "gf": 0, "ga": 0}
    for g in games:
        if g.get("gameType") != game_type or g.get("gameState") not in FINAL_STATES:
            continue
        res, ours, theirs = result_of(g, team)
        rec["gp"] += 1
        rec[res.lower()] += 1
        rec["gf"] += ours
        rec["ga"] += theirs
    return rec


def period_label(game: Dict[str, Any]) -> str:
    pd = game.get("periodDescriptor") or {}
    num, ptype = int(pd.get("number") or 1), pd.get("periodType", "REG")
    if ptype == "SO":
        return "Shootout"
    if ptype == "OT":
        return "OT" if num <= 4 else f"{num - 3}OT"
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(num, f"P{num}")


def goal_lines(goals: List[dict]) -> List[str]:
    lines = []
    for g in goals or []:
        team = name_of(g.get("teamAbbrev"))
        who = f"{name_of(g.get('firstName'))} {name_of(g.get('lastName'))}".strip() or name_of(g.get("name"))
        period = (g.get("periodDescriptor") or {}).get("number") or g.get("period") or "?"
        ptype = (g.get("periodDescriptor") or {}).get("periodType", "")
        plabel = {"OT": "OT", "SO": "SO"}.get(ptype, f"P{period}")
        strength = str(g.get("strength", "")).lower()
        tag = {"pp": " (PPG)", "sh": " (SHG)"}.get(strength, "")
        if g.get("goalModifier") == "empty-net":
            tag += " (EN)"
        lines.append(f"{plabel} {g.get('timeInPeriod', '')}  [{team}] {who}{tag}")
    return lines


def landing_summary(landing: Dict[str, Any]) -> Dict[str, Any]:
    summary = landing.get("summary") or {}
    stars = []
    for s in summary.get("threeStars") or []:
        stars.append(
            f"\u2605{s.get('star', '?')}  {name_of(s.get('name'))} ({name_of(s.get('teamAbbrev'))})"
            f"  {s.get('goals', 0)}G {s.get('assists', 0)}A"
            if "goals" in s else
            f"\u2605{s.get('star', '?')}  {name_of(s.get('name'))} ({name_of(s.get('teamAbbrev'))})"
        )
    goals: List[dict] = []
    for period in summary.get("scoring") or []:
        for g in period.get("goals") or []:
            g = dict(g)
            g.setdefault("periodDescriptor", period.get("periodDescriptor"))
            goals.append(g)
    return {"stars": stars, "goals": goal_lines(goals)}


def scoring_leaders(stats: Dict[str, Any], n: int = 8) -> List[dict]:
    skaters = list(stats.get("skaters") or [])
    skaters.sort(key=lambda s: (s.get("points", 0), s.get("goals", 0)), reverse=True)
    return skaters[:n]


def parse_roster(data: Dict[str, Any]) -> Dict[str, List[dict]]:
    out = {}
    for key, label in (("forwards", "Forwards"), ("defensemen", "Defense"), ("goalies", "Goalies")):
        players = []
        for p in data.get(key) or []:
            players.append({
                "id": p.get("id"),
                "num": p.get("sweaterNumber", ""),
                "name": f"{name_of(p.get('firstName'))} {name_of(p.get('lastName'))}".strip(),
                "pos": p.get("positionCode", ""),
                "hand": p.get("shootsCatches", ""),
                "from": ", ".join(x for x in (name_of(p.get("birthCity")), p.get("birthCountry", "")) if x),
            })
        players.sort(key=lambda p: (int(p["num"]) if str(p["num"]).isdigit() else 999))
        out[label] = players
    return out


class GoalTracker:
    """Detect new goals for one team, resetting cleanly between games.

    Starting the app mid-game sets a baseline without a false horn, and a
    new game id resets the baseline so the horn fires again the next night.
    """

    def __init__(self) -> None:
        self.game_id: Any = None
        self.score: Optional[int] = None

    def update(self, game_id: Any, score: int) -> bool:
        if game_id != self.game_id:
            self.game_id, self.score = game_id, score
            return False
        new_goal = self.score is not None and score > self.score
        self.score = score
        return new_goal


# ---------------------------------------------------------------- news parsing
_ATOM = "{http://www.w3.org/2005/Atom}"
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,200}$")


_DRUPAL_DATE = "%A, %B %d, %Y - %H:%M"    # e.g. "Wednesday, September 30, 2026 - 15:15"


def _ts(value: Optional[str]) -> float:
    """Best-effort timestamp from RFC 822 (RSS), ISO 8601 (Atom/JSON) or Drupal dates."""
    if not value:
        return 0.0
    value = value.strip()
    try:
        return parsedate_to_datetime(value).timestamp()
    except (TypeError, ValueError, IndexError):
        pass
    dt = parse_utc(value)
    if dt:
        return dt.timestamp()
    try:
        return datetime.strptime(value, _DRUPAL_DATE).timestamp()   # naive -> local time
    except ValueError:
        return 0.0


def _item(source: str, title: Any, link: Any, desc: Any, ts: float) -> Dict[str, Any]:
    return {"source": source, "title": clean_text(title, 200), "link": str(link or "").strip(),
            "desc": clean_text(desc, 260), "ts": ts}


def parse_feed(raw: bytes, source: str = "", limit: int = 20) -> List[Dict[str, Any]]:
    """Parse RSS 2.0 or Atom defensively.

    DTDs/entities are rejected outright (no entity-expansion attacks), and all
    text is sanitized. Links are returned as-is; callers must validate them
    with ``net.is_safe_browser_url`` before opening.
    """
    raw = raw.lstrip()
    lowered = raw.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise ValueError("Feed contains a DTD/entity declaration; refusing to parse")
    if not lowered[:200].startswith((b"<?xml", b"<rss", b"<feed")):
        raise ValueError("Not an XML feed")
    root = ET.fromstring(raw)
    items: List[Dict[str, Any]] = []
    channel = root.find("channel")
    if channel is not None:                                   # RSS 2.0
        for it in channel.findall("item")[:limit]:
            items.append(_item(source, it.findtext("title"), it.findtext("link"),
                               it.findtext("description"), _ts(it.findtext("pubDate"))))
    elif root.tag == _ATOM + "feed":                          # Atom (e.g. Reddit, YouTube)
        _MRSS = "{http://search.yahoo.com/mrss/}"
        for en in root.findall(_ATOM + "entry")[:limit]:
            link = en.find(_ATOM + "link")
            desc = (en.findtext(_ATOM + "summary")
                    or en.findtext(f"{_MRSS}group/{_MRSS}description")
                    or en.findtext(_ATOM + "content") or "")
            items.append(_item(source, en.findtext(_ATOM + "title"),
                               link.get("href") if link is not None else "",
                               desc, _ts(en.findtext(_ATOM + "updated") or en.findtext(_ATOM + "published"))))
    return items


def parse_forge(data: Dict[str, Any], source: str = "NHL.com (official)") -> List[Dict[str, Any]]:
    items = []
    for it in data.get("items") or []:
        slug = str(it.get("slug") or "")
        if not _SLUG_RE.match(slug):
            continue
        items.append(_item(source, it.get("headline") or it.get("title"),
                           f"https://www.nhl.com/news/{slug}", it.get("summary"), _ts(it.get("contentDate"))))
    return items


def parse_espn(data: Dict[str, Any], source: str = "ESPN") -> List[Dict[str, Any]]:
    items = []
    for a in data.get("articles") or []:
        link = ((a.get("links") or {}).get("web") or {}).get("href") or ""
        if link.startswith("http://"):
            link = "https://" + link[len("http://"):]
        items.append(_item(source, a.get("headline"), link, a.get("description"), _ts(a.get("published"))))
    return items


def merge_news(*lists: List[Dict[str, Any]], per_source: int = 15) -> List[Dict[str, Any]]:
    """Newest first, de-duplicated. Capped per source so no site is crowded out."""
    seen, out = set(), []
    for item in sorted((i for lst in lists for i in lst[:per_source]), key=lambda i: i["ts"], reverse=True):
        key = item["title"].lower()[:80]
        if item["title"] and key not in seen:
            seen.add(key)
            out.append(item)
    return out


def ago(ts: float, now: Optional[float] = None) -> str:
    if not ts:
        return ""
    secs = max(0, int((now or time.time()) - ts))
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if secs >= size:
            return f"{secs // size}{unit} ago"
    return "just now"


# ---------------------------------------------------------------- teams & venue
TEAM_NAMES = {
    "ANA": "Anaheim Ducks", "BOS": "Boston Bruins", "BUF": "Buffalo Sabres", "CGY": "Calgary Flames",
    "CAR": "Carolina Hurricanes", "CHI": "Chicago Blackhawks", "COL": "Colorado Avalanche",
    "CBJ": "Columbus Blue Jackets", "DAL": "Dallas Stars", "DET": "Detroit Red Wings",
    "EDM": "Edmonton Oilers", "FLA": "Florida Panthers", "LAK": "Los Angeles Kings", "MIN": "Minnesota Wild",
    "MTL": "Montr\u00e9al Canadiens", "NSH": "Nashville Predators", "NJD": "New Jersey Devils",
    "NYI": "New York Islanders", "NYR": "New York Rangers", "OTT": "Ottawa Senators",
    "PHI": "Philadelphia Flyers", "PIT": "Pittsburgh Penguins", "SJS": "San Jose Sharks",
    "SEA": "Seattle Kraken", "STL": "St. Louis Blues", "TBL": "Tampa Bay Lightning",
    "TOR": "Toronto Maple Leafs", "UTA": "Utah Mammoth", "VAN": "Vancouver Canucks",
    "VGK": "Vegas Golden Knights", "WSH": "Washington Capitals", "WPG": "Winnipeg Jets",
}


def team_full_name(team: Dict[str, Any]) -> str:
    place, common = name_of(team.get("placeName")), name_of(team.get("commonName"))
    if place and common:
        return f"{place} {common}"
    abbrev = name_of(team.get("abbrev"))
    return TEAM_NAMES.get(abbrev) or common or name_of(team.get("name")) or place or abbrev


def enrich(live: Optional[Dict[str, Any]], scheduled: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Overlay a live scoreboard game on its schedule entry.

    ``score/now`` omits city/full names (and sometimes TV); the season
    schedule has them. Live values always win.
    """
    if not scheduled:
        return dict(live or {})
    out = dict(scheduled)
    out.update(live or {})
    for side in ("homeTeam", "awayTeam"):
        out[side] = {**(scheduled.get(side) or {}), **((live or {}).get(side) or {})}
    for key in ("venue", "tvBroadcasts"):
        if not (live or {}).get(key) and scheduled.get(key):
            out[key] = scheduled[key]
    return out


def matchup_line(game: Dict[str, Any], team: str) -> str:
    is_home, _, them = perspective(game, team)
    return f"{'vs' if is_home else '@'} {team_full_name(them)}"


def venue_line(game: Dict[str, Any]) -> str:
    venue = name_of(game.get("venue"))
    home = game.get("homeTeam") or {}
    city = name_of(home.get("placeName"))
    return " \u00b7 ".join(x for x in (venue, city) if x)


def broadcasts(game: Dict[str, Any], team: Optional[str] = None) -> str:
    """US TV networks. With ``team``, only national feeds and that team's market."""
    markets = None
    if team:
        markets = ("N", "H") if perspective(game, team)[0] else ("N", "A")
    nets: List[str] = []
    for b in game.get("tvBroadcasts") or []:
        if b.get("countryCode") != "US" or not b.get("network"):
            continue
        if markets and b.get("market") not in markets:
            continue
        if b["network"] not in nets:
            nets.append(str(b["network"]))
    return ", ".join(nets[:4])


def last_scorer(goals: List[dict], team: str) -> str:
    for g in reversed(goals or []):
        if name_of(g.get("teamAbbrev")) == team:
            who = f"{name_of(g.get('firstName'))} {name_of(g.get('lastName'))}".strip()
            return who or name_of(g.get("name"))
    return ""


def upcoming_games(games: List[dict], n: int = 10) -> List[dict]:
    rest = [g for g in games if g.get("gameState") not in FINAL_STATES]
    return sorted(rest, key=lambda g: g.get("startTimeUTC", ""))[:n]


# ---------------------------------------------------------------- live situation
def situation(*sources: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Power-play / empty-net state from a live landing or scoreboard game.

    situationCode is four digits: away goalie (1/0), away skaters,
    home skaters, home goalie (1/0). e.g. 1451 = home on a 5-on-4 PP.
    """
    for src in sources:
        sit = (src or {}).get("situation") or {}
        code = str(sit.get("situationCode") or "")
        if len(code) == 4 and code.isdigit():
            away_g, away_s, home_s, home_g = (int(c) for c in code)
            away = (src.get("awayTeam") or {}).get("abbrev", "AWAY")
            home = (src.get("homeTeam") or {}).get("abbrev", "HOME")
            out = {"strength": f"{away_s}v{home_s}", "pp": None, "empty_net": [],
                   "advantage": f"{max(away_s, home_s)}-on-{min(away_s, home_s)}",
                   "time": sit.get("timeRemaining", "")}
            # A pulled goalie adds an extra attacker; that alone is not a power play.
            eff_away = away_s - (1 if away_g == 0 else 0)
            eff_home = home_s - (1 if home_g == 0 else 0)
            if eff_away > eff_home:
                out["pp"] = away
            elif eff_home > eff_away:
                out["pp"] = home
            if away_g == 0:
                out["empty_net"].append(away)
            if home_g == 0:
                out["empty_net"].append(home)
            return out
    return {}


def penalty_lines(landing: Dict[str, Any], limit: int = 12) -> List[str]:
    lines = []
    for period in (landing.get("summary") or {}).get("penalties") or []:
        plabel = period_label({"periodDescriptor": period.get("periodDescriptor") or {}})
        for p in period.get("penalties") or []:
            who = p.get("committedByPlayer") or {}
            if isinstance(who, dict):
                name = f"{name_of(who.get('firstName'))} {name_of(who.get('lastName'))}".strip()
            else:
                name = name_of(who)
            infraction = str(p.get("descKey", "")).replace("-", " ")
            lines.append(f"{plabel} {p.get('timeInPeriod', '')}  [{name_of(p.get('teamAbbrev'))}] "
                         f"{name or 'Bench'} \u2013 {infraction} ({p.get('duration', '?')} min)")
    return lines[-limit:]


# ---------------------------------------------------------------- standings
def standings_tables(data: Dict[str, Any], division: str, conference: str) -> Dict[str, List[dict]]:
    rows = list(data.get("standings") or [])
    div = sorted((r for r in rows if r.get("divisionAbbrev") == division),
                 key=lambda r: r.get("divisionSequence", 99))
    conf = [r for r in rows if r.get("conferenceAbbrev") == conference]
    leaders = [r for r in conf if r.get("divisionSequence", 99) <= 3]
    leaders.sort(key=lambda r: (r.get("divisionAbbrev", ""), r.get("divisionSequence", 99)))
    wild = sorted((r for r in conf if r.get("divisionSequence", 99) > 3),
                  key=lambda r: r.get("wildcardSequence", 99))
    return {"division": div, "leaders": leaders, "wildcard": wild}


def standings_row(r: Dict[str, Any]) -> List[Any]:
    streak = f"{r.get('streakCode', '')}{r.get('streakCount', '')}" if r.get("streakCode") else ""
    l10 = f"{r.get('l10Wins', 0)}-{r.get('l10Losses', 0)}-{r.get('l10OtLosses', 0)}"
    pct = r.get("pointPctg")
    return [name_of(r.get("teamAbbrev")), r.get("gamesPlayed", 0), r.get("wins", 0), r.get("losses", 0),
            r.get("otLosses", 0), r.get("points", 0), f"{pct:.3f}" if isinstance(pct, (int, float)) else "-",
            r.get("goalDifferential", 0), l10, streak]


# ---------------------------------------------------------------- player cards
def player_card(d: Dict[str, Any]) -> Dict[str, Any]:
    first, last = name_of(d.get("firstName")), name_of(d.get("lastName"))
    h = d.get("heightInInches")
    height = f"{h // 12}'{h % 12}\"" if isinstance(h, int) else ""
    born = d.get("birthDate", "")
    age = ""
    try:
        b = datetime.strptime(born, "%Y-%m-%d").date()
        today = datetime.now().date()
        age = str(today.year - b.year - ((today.month, today.day) < (b.month, b.day)))
    except ValueError:
        pass
    draft = d.get("draftDetails") or {}
    draft_txt = (f"{draft.get('year')} \u00b7 Rd {draft.get('round')} \u00b7 #{draft.get('overallPick')} "
                 f"({draft.get('teamAbbrev', '')})") if draft.get("year") else "Undrafted"
    feat = ((d.get("featuredStats") or {}).get("regularSeason") or {}).get("subSeason") or {}
    season_id = str((d.get("featuredStats") or {}).get("season") or "")
    season_label = f"{season_id[:4]}-{season_id[6:]}" if len(season_id) == 8 and season_id.isdigit() else ""
    career = (d.get("careerTotals") or {}).get("regularSeason") or {}
    return {
        "name": f"{first} {last}".strip(), "num": d.get("sweaterNumber", ""), "pos": d.get("position", ""),
        "headshot": d.get("headshot", ""), "age": age, "height": height,
        "weight": f"{d.get('weightInPounds')} lb" if d.get("weightInPounds") else "",
        "hand": d.get("shootsCatches", ""),
        "from": ", ".join(x for x in (name_of(d.get("birthCity")), name_of(d.get("birthStateProvince")),
                                      d.get("birthCountry", "")) if x),
        "draft": draft_txt, "season": feat, "season_label": season_label, "career": career,
        "last5": d.get("last5Games") or [],
    }


# ---------------------------------------------------------------- versions
def version_tuple(v: str) -> Tuple[int, ...]:
    nums = re.findall(r"\d+", v or "")
    return tuple(int(n) for n in nums[:3]) or (0,)

