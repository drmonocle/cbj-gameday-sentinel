"""Static configuration: endpoints, host allowlists, limits, palette."""
from __future__ import annotations

from . import __version__

APP_NAME = "CBJ Gameday Sentinel"
APP_ID = "CBJGamedaySentinel"
TEAM = "CBJ"
TEAM_DIVISION = "M"     # Metropolitan
TEAM_CONFERENCE = "E"   # Eastern
ESPN_TEAM_ID = 29
NHL_TEAM_ID = 29

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
URL_PLAYER = NHL_API + "/player/{player_id}/landing"
URL_GITHUB_LATEST = "https://api.github.com/repos/{repo}/releases/latest"

NEWS_SOURCES = (
    {"id": "nhl", "name": "NHL.com (official)", "kind": "forge",
     "url": f"https://forge-dapi.d3.nhle.com/v2/content/en-us/stories?tags.slug=teamid-{NHL_TEAM_ID}&context.slug=nhl&$limit=15"},
    {"id": "espn", "name": "ESPN", "kind": "espn",
     "url": f"https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/news?team={ESPN_TEAM_ID}&limit=15"},
    {"id": "cannon", "name": "The Cannon", "kind": "feed", "url": "https://www.jacketscannon.com/feed/"},
    {"id": "1ob", "name": "1st Ohio Battery", "kind": "feed", "url": "https://www.1stohiobattery.com/feed"},
    {"id": "reddit", "name": "r/BlueJackets", "kind": "feed", "url": "https://www.reddit.com/r/BlueJackets/.rss"},
)

NHL_WEB = "https://www.nhl.com"
OFFICIAL_NEWS_URL = f"{NHL_WEB}/bluejackets/news"

# Where the "Watch" button goes. Prime Video hosts the Blue Jackets Hockey
# Network for in-market fans (Ohio, Kentucky, West Virginia); this is the
# channel page the team's own cbj.co/subscribe link redirects to.
WATCH_OPTIONS = {
    "prime": ("Prime Video \u00b7 Blue Jackets Hockey Network",
              "https://www.amazon.com/gp/video/channel/19bfae52-c58d-83c8-3909-2f61654f1afb"),
    "espn": ("ESPN+ \u00b7 NHL Power Play (out-of-market)", "https://plus.espn.com/nhl"),
    "fubo": ("Fubo", "https://www.fubo.tv/"),
    "nhl": ("NHL.com where-to-watch guide", f"{NHL_WEB}/bluejackets/fans/tune-in"),
}

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
})
# The Blue Jackets logo is a trademark of the club. It is not stored in this
# repository; the app downloads it for display and caches it in %APPDATA%.
LOGO_URL = "https://a.espncdn.com/i/teamlogos/nhl/500/cbj.png"
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
NAVY = "#041E42"
RED = "#C8102E"
SILVER = "#A2AAAD"
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
