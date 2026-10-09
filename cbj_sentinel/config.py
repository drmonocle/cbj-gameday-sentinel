"""Static configuration: endpoints, host allowlists, limits, palette."""
from __future__ import annotations

import os
from . import __version__

# ==============================================================================
# 32-TEAM NHL PRESET CATALOG
# Easily interchangeable for any team: simply change TEAM = "..." below
# or launch with the environment variable NHL_SENTINEL_TEAM="TOR".
# ==============================================================================
TEAM_PRESETS = {
    # Metropolitan (Eastern)
    "CAR": {"name": "Carolina Hurricanes", "short": "Hurricanes", "city": "Raleigh", "division": "M", "conference": "E", "nhl_id": 12, "espn_id": 7, "primary": "#CC0000", "secondary": "#000000", "accent": "#A2AAAD", "subreddit": "canes"},
    "CBJ": {"name": "Columbus Blue Jackets", "short": "Blue Jackets", "city": "Columbus", "division": "M", "conference": "E", "nhl_id": 29, "espn_id": 29, "primary": "#041E42", "secondary": "#C8102E", "accent": "#A2AAAD", "subreddit": "BlueJackets"},
    "NJD": {"name": "New Jersey Devils", "short": "Devils", "city": "New Jersey", "division": "M", "conference": "E", "nhl_id": 1, "espn_id": 11, "primary": "#CE1126", "secondary": "#000000", "accent": "#FFFFFF", "subreddit": "devils"},
    "NYI": {"name": "New York Islanders", "short": "Islanders", "city": "New York", "division": "M", "conference": "E", "nhl_id": 2, "espn_id": 12, "primary": "#00539B", "secondary": "#F47920", "accent": "#FFFFFF", "subreddit": "NewYorkIslanders"},
    "NYR": {"name": "New York Rangers", "short": "Rangers", "city": "New York", "division": "M", "conference": "E", "nhl_id": 3, "espn_id": 13, "primary": "#0038A8", "secondary": "#CE1126", "accent": "#FFFFFF", "subreddit": "rangers"},
    "PHI": {"name": "Philadelphia Flyers", "short": "Flyers", "city": "Philadelphia", "division": "M", "conference": "E", "nhl_id": 4, "espn_id": 15, "primary": "#F74902", "secondary": "#000000", "accent": "#FFFFFF", "subreddit": "Flyers"},
    "PIT": {"name": "Pittsburgh Penguins", "short": "Penguins", "city": "Pittsburgh", "division": "M", "conference": "E", "nhl_id": 5, "espn_id": 16, "primary": "#000000", "secondary": "#FCB514", "accent": "#CFC493", "subreddit": "penguins"},
    "WSH": {"name": "Washington Capitals", "short": "Capitals", "city": "Washington", "division": "M", "conference": "E", "nhl_id": 15, "espn_id": 23, "primary": "#041E42", "secondary": "#C8102E", "accent": "#FFFFFF", "subreddit": "capitals"},

    # Atlantic (Eastern)
    "BOS": {"name": "Boston Bruins", "short": "Bruins", "city": "Boston", "division": "A", "conference": "E", "nhl_id": 6, "espn_id": 1, "primary": "#000000", "secondary": "#FFB81C", "accent": "#FFFFFF", "subreddit": "BostonBruins"},
    "BUF": {"name": "Buffalo Sabres", "short": "Sabres", "city": "Buffalo", "division": "A", "conference": "E", "nhl_id": 7, "espn_id": 2, "primary": "#002654", "secondary": "#FCB514", "accent": "#ADAFAA", "subreddit": "sabres"},
    "DET": {"name": "Detroit Red Wings", "short": "Red Wings", "city": "Detroit", "division": "A", "conference": "E", "nhl_id": 17, "espn_id": 5, "primary": "#CE1126", "secondary": "#FFFFFF", "accent": "#CE1126", "subreddit": "DetroitRedWings"},
    "FLA": {"name": "Florida Panthers", "short": "Panthers", "city": "Sunrise", "division": "A", "conference": "E", "nhl_id": 13, "espn_id": 26, "primary": "#041E42", "secondary": "#C8102E", "accent": "#B9975B", "subreddit": "FloridaPanthers"},
    "MTL": {"name": "Montreal Canadiens", "short": "Canadiens", "city": "Montreal", "division": "A", "conference": "E", "nhl_id": 8, "espn_id": 10, "primary": "#AF1E2D", "secondary": "#192168", "accent": "#FFFFFF", "subreddit": "Habs"},
    "OTT": {"name": "Ottawa Senators", "short": "Senators", "city": "Ottawa", "division": "A", "conference": "E", "nhl_id": 9, "espn_id": 14, "primary": "#C8102E", "secondary": "#000000", "accent": "#D69F0F", "subreddit": "OttawaSenators"},
    "TBL": {"name": "Tampa Bay Lightning", "short": "Lightning", "city": "Tampa", "division": "A", "conference": "E", "nhl_id": 14, "espn_id": 20, "primary": "#002868", "secondary": "#FFFFFF", "accent": "#002868", "subreddit": "TampaBayLightning"},
    "TOR": {"name": "Toronto Maple Leafs", "short": "Maple Leafs", "city": "Toronto", "division": "A", "conference": "E", "nhl_id": 10, "espn_id": 21, "primary": "#00205B", "secondary": "#FFFFFF", "accent": "#00205B", "subreddit": "leafs"},

    # Central (Western)
    "CHI": {"name": "Chicago Blackhawks", "short": "Blackhawks", "city": "Chicago", "division": "C", "conference": "W", "nhl_id": 16, "espn_id": 4, "primary": "#CF0A2C", "secondary": "#000000", "accent": "#FFD100", "subreddit": "hawks"},
    "COL": {"name": "Colorado Avalanche", "short": "Avalanche", "city": "Denver", "division": "C", "conference": "W", "nhl_id": 21, "espn_id": 17, "primary": "#6F263D", "secondary": "#236192", "accent": "#A2AAAD", "subreddit": "ColoradoAvalanche"},
    "DAL": {"name": "Dallas Stars", "short": "Stars", "city": "Dallas", "division": "C", "conference": "W", "nhl_id": 25, "espn_id": 9, "primary": "#006847", "secondary": "#8F8F8C", "accent": "#111111", "subreddit": "DallasStars"},
    "MIN": {"name": "Minnesota Wild", "short": "Wild", "city": "Saint Paul", "division": "C", "conference": "W", "nhl_id": 30, "espn_id": 30, "primary": "#154734", "secondary": "#A6192E", "accent": "#EAAA00", "subreddit": "wildhockey"},
    "NSH": {"name": "Nashville Predators", "short": "Predators", "city": "Nashville", "division": "C", "conference": "W", "nhl_id": 18, "espn_id": 27, "primary": "#FFB81C", "secondary": "#041E42", "accent": "#FFFFFF", "subreddit": "Predators"},
    "STL": {"name": "St. Louis Blues", "short": "Blues", "city": "St. Louis", "division": "C", "conference": "W", "nhl_id": 19, "espn_id": 19, "primary": "#002F87", "secondary": "#FCB514", "accent": "#041E42", "subreddit": "stlouisblues"},
    "UTA": {"name": "Utah Mammoth", "short": "Mammoth", "city": "Salt Lake City", "division": "C", "conference": "W", "nhl_id": 59, "espn_id": 140656, "primary": "#010101", "secondary": "#69B3E7", "accent": "#FFFFFF", "subreddit": "Utah_Hockey"},
    "WPG": {"name": "Winnipeg Jets", "short": "Jets", "city": "Winnipeg", "division": "C", "conference": "W", "nhl_id": 52, "espn_id": 28, "primary": "#041E42", "secondary": "#004C97", "accent": "#AC162C", "subreddit": "winnipegjets"},

    # Pacific (Western)
    "ANA": {"name": "Anaheim Ducks", "short": "Ducks", "city": "Anaheim", "division": "P", "conference": "W", "nhl_id": 24, "espn_id": 25, "primary": "#F47A38", "secondary": "#B9975B", "accent": "#000000", "subreddit": "AnaheimDucks"},
    "CGY": {"name": "Calgary Flames", "short": "Flames", "city": "Calgary", "division": "P", "conference": "W", "nhl_id": 20, "espn_id": 3, "primary": "#C8102E", "secondary": "#F1BE48", "accent": "#111111", "subreddit": "CalgaryFlames"},
    "EDM": {"name": "Edmonton Oilers", "short": "Oilers", "city": "Edmonton", "division": "P", "conference": "W", "nhl_id": 22, "espn_id": 6, "primary": "#041E42", "secondary": "#FF4C00", "accent": "#FFFFFF", "subreddit": "EdmontonOilers"},
    "LAK": {"name": "Los Angeles Kings", "short": "Kings", "city": "Los Angeles", "division": "P", "conference": "W", "nhl_id": 26, "espn_id": 8, "primary": "#111111", "secondary": "#A2AAAD", "accent": "#FFFFFF", "subreddit": "losangeleskings"},
    "SJS": {"name": "San Jose Sharks", "short": "Sharks", "city": "San Jose", "division": "P", "conference": "W", "nhl_id": 28, "espn_id": 18, "primary": "#006D75", "secondary": "#EA7200", "accent": "#000000", "subreddit": "SanJoseSharks"},
    "SEA": {"name": "Seattle Kraken", "short": "Kraken", "city": "Seattle", "division": "P", "conference": "W", "nhl_id": 55, "espn_id": 124292, "primary": "#001628", "secondary": "#99D9D9", "accent": "#E9072B", "subreddit": "SeattleKraken"},
    "VAN": {"name": "Vancouver Canucks", "short": "Canucks", "city": "Vancouver", "division": "P", "conference": "W", "nhl_id": 23, "espn_id": 22, "primary": "#00205B", "secondary": "#00843D", "accent": "#041C2C", "subreddit": "canucks"},
    "VGK": {"name": "Vegas Golden Knights", "short": "Golden Knights", "city": "Las Vegas", "division": "P", "conference": "W", "nhl_id": 54, "espn_id": 37, "primary": "#B4975A", "secondary": "#333F48", "accent": "#000000", "subreddit": "goldenknights"},
}

# Change this single variable (or set environment variable NHL_SENTINEL_TEAM)
# to re-brand the app for any NHL team!
TEAM = os.environ.get("NHL_SENTINEL_TEAM", "CBJ").upper()
if TEAM not in TEAM_PRESETS:
    TEAM = "CBJ"

_p = TEAM_PRESETS[TEAM]
APP_NAME = f"{_p['short']} Gameday Sentinel" if TEAM != "CBJ" else "CBJ Gameday Sentinel"
APP_ID = f"{TEAM}GamedaySentinel" if TEAM != "CBJ" else "CBJGamedaySentinel"
TEAM_NAME = _p["name"]
TEAM_SHORT = _p["short"]
# nhl.com URL path segment for the club's pages (differs from the nickname for Utah).
NHL_TEAM_SLUG = {"UTA": "utah"}.get(TEAM, _p["short"].lower().replace(" ", ""))
# ESPN's logo file names are not always the NHL tricode.
_LOGO_SLUGS = {"NJD": "nj", "TBL": "tb", "SJS": "sj", "LAK": "la"}
TEAM_DIVISION = _p["division"]
TEAM_CONFERENCE = _p["conference"]
ESPN_TEAM_ID = _p["espn_id"]
NHL_TEAM_ID = _p["nhl_id"]

# Public repo used for the once-a-day "new version available" check
# (empty string = check disabled).
GITHUB_REPO = "drmonocle/cbj-gameday-sentinel"
REPO_URL = f"https://github.com/{GITHUB_REPO}" if GITHUB_REPO else "https://github.com/"

# Identify honestly to upstream servers instead of spoofing a browser.
USER_AGENT = f"{APP_ID}/{__version__} (+{REPO_URL})"

# --- Data sources (public, unauthenticated, read-only) ---
NHL_API = "https://api-web.nhle.com/v1"
URL_SCORE_NOW = f"{NHL_API}/score/now"
URL_SCHEDULE = f"{NHL_API}/club-schedule-season/{TEAM}/now"
URL_CLUB_STATS = f"{NHL_API}/club-stats/{TEAM}/now"
URL_ROSTER = f"{NHL_API}/roster/{TEAM}/current"
URL_STANDINGS = f"{NHL_API}/standings/now"
URL_BOXSCORE = NHL_API + "/gamecenter/{game_id}/boxscore"
URL_LANDING = NHL_API + "/gamecenter/{game_id}/landing"
URL_PLAY_BY_PLAY = NHL_API + "/gamecenter/{game_id}/play-by-play"
URL_PLAYER = NHL_API + "/player/{player_id}/landing"
URL_GITHUB_LATEST = "https://api.github.com/repos/{repo}/releases/latest"

NEWS_SOURCES = (
    {"id": "nhl", "name": "NHL.com (official)", "kind": "forge",
     "url": f"https://forge-dapi.d3.nhle.com/v2/content/en-us/stories?tags.slug=teamid-{NHL_TEAM_ID}&context.slug=nhl&$limit=15"},
    {"id": "espn", "name": "ESPN", "kind": "espn",
     "url": f"https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/news?team={ESPN_TEAM_ID}&limit=15"},
    {"id": "reddit", "name": f"r/{_p['subreddit']}", "kind": "feed",
     "url": f"https://www.reddit.com/r/{_p['subreddit']}/.rss"},
)
if TEAM == "CBJ":
    NEWS_SOURCES = NEWS_SOURCES + (
        {"id": "cannon", "name": "The Cannon", "kind": "feed", "url": "https://www.jacketscannon.com/feed/"},
        {"id": "1ob", "name": "1st Ohio Battery", "kind": "feed", "url": "https://www.1stohiobattery.com/feed"},
        {"id": "yt_cbj", "name": "YouTube \u00b7 Blue Jackets", "kind": "feed",
         "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCxdPjcb73fJilPpcRxgzi3A"},
        {"id": "yt_lockedon", "name": "YouTube \u00b7 Locked On CBJ", "kind": "feed",
         "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC9Tsndgsrew5fjeXhsdHYhw"},
        {"id": "yt_nhl", "name": "YouTube \u00b7 NHL Highlights", "kind": "yt_filter",
         "filter": "blue jackets,cbj,columbus",
         "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCqFMzb-4AUf6WAIbl132QKA"},
    )

REDDIT_NAME = f"r/{_p['subreddit']}"

NHL_WEB = "https://www.nhl.com"
OFFICIAL_NEWS_URL = f"{NHL_WEB}/{NHL_TEAM_SLUG}/news"

# Where the "Watch" button goes. Prime Video hosts the Blue Jackets Hockey
# Network for in-market fans (Ohio, Kentucky, West Virginia); this is the
# channel page the team's own cbj.co/subscribe link redirects to.
WATCH_OPTIONS = {
    "espn": ("ESPN+ \u00b7 NHL Power Play (out-of-market)", "https://plus.espn.com/nhl"),
    "fubo": ("Fubo", "https://www.fubo.tv/"),
    "nhl": ("NHL.com where-to-watch guide", f"{NHL_WEB}/{NHL_TEAM_SLUG}/fans/tune-in"),
}
DEFAULT_WATCH = "nhl"
if TEAM == "CBJ":
    WATCH_OPTIONS = {"prime": ("Prime Video \u00b7 Blue Jackets Hockey Network",
                               "https://www.amazon.com/gp/video/channel/19bfae52-c58d-83c8-3909-2f61654f1afb"),
                     **WATCH_OPTIONS}
    DEFAULT_WATCH = "prime"

# --- Security allowlists (HTTPS only; exact host match) ---
# Hosts the app may download from. Redirects are re-checked against this list.
FETCH_HOSTS = frozenset({
    "api-web.nhle.com",          # scores, schedule, stats, roster, standings
    "forge-dapi.d3.nhle.com",    # official NHL.com team news
    "assets.nhle.com",           # player headshots (shown in player cards)
    "site.api.espn.com",         # ESPN team news
    "www.jacketscannon.com",     # The Cannon (SB Nation) RSS
    "www.1stohiobattery.com",    # 1st Ohio Battery RSS
    "www.reddit.com",            # r/BlueJackets public RSS
    "api.github.com",            # optional update check
    "a.espncdn.com",             # team logo (downloaded once, cached locally)
    "www.youtube.com",           # YouTube channel feeds (Atom RSS)
})
# The Blue Jackets logo is a trademark of the club. It is not stored in this
# repository; the app downloads it for display and caches it in %APPDATA%.
LOGO_URL = f"https://a.espncdn.com/i/teamlogos/nhl/500/{_LOGO_SLUGS.get(TEAM, TEAM.lower())}.png"
LOGO_MAX_AGE_DAYS = 30
# Hosts the app may open in the user's browser.
BROWSER_HOSTS = frozenset({
    "www.nhl.com", "nhl.com",
    "www.amazon.com", "amazon.com", "www.primevideo.com", "primevideo.com",
    "plus.espn.com", "www.espn.com", "espn.com",
    "www.fubo.tv", "fubo.tv",
    "www.jacketscannon.com", "jacketscannon.com",
    "www.1stohiobattery.com", "1stohiobattery.com",
    "www.reddit.com", "reddit.com", "old.reddit.com",
    "www.youtube.com", "youtube.com", "youtu.be",
    "github.com",
})

MAX_JSON_BYTES = 5 * 1024 * 1024
MAX_FEED_BYTES = 3 * 1024 * 1024
MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_CUSTOM_WAV_BYTES = 10 * 1024 * 1024
MAX_CUSTOM_WAV_SECONDS = 30
HTTP_TIMEOUT = 10
MAX_REDIRECTS = 3

# --- Polling cadence (seconds). Kept polite since many fans may run this. ---
POLL_LIVE = 20
POLL_GAMEDAY = 60
POLL_IDLE = 300
SLOW_REFRESH = 300
NEWS_REFRESH = 1800
UPDATE_CHECK = 24 * 3600

# --- Palette (team-inspired colors) ---
NAVY = _p.get("primary", "#041E42")
RED = _p.get("secondary", "#C8102E")
SILVER = _p.get("accent", "#A2AAAD")
BG = "#0b1523"
CARD = "#14243b"
CARD_DEEP = "#0d1827"
HILITE = "#1d3557"
BAR = "#08101a"
TEXT = "#FFFFFF"
MUTED = "#8fa3bf"
ACCENT = "#29b6f6"
GREEN = "#00c853"
GOLD = "#ffd700"
FONT = "Segoe UI"
