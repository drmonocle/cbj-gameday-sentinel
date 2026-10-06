# 🏒 Forking & Customizing for Any of the 32 NHL Teams

**CBJ Gameday Sentinel** was built with modular architecture designed to make forking and re-branding for **any of the 32 NHL franchises** effortless.

Whether you want to build a **Toronto Maple Leafs**, **New York Rangers**, **Boston Bruins**, or **Edmonton Oilers** desktop companion, everything can be re-keyed in seconds.

---

## ⚡ Quick Test (Zero-Code Runtime Override)

You can run the app as any NHL team without changing a single line of code by using the `NHL_SENTINEL_TEAM` environment variable:

```powershell
# Run as Toronto Maple Leafs
$env:NHL_SENTINEL_TEAM = "TOR"
py run_sentinel.pyw

# Run as Boston Bruins
$env:NHL_SENTINEL_TEAM = "BOS"
py run_sentinel.pyw

# Run as Edmonton Oilers
$env:NHL_SENTINEL_TEAM = "EDM"
py run_sentinel.pyw
```

The application will automatically pull that franchise's schedule, live scores, team roster, statistics, official news, and ESPN high-res vector logos.

---

## 🚀 Step-by-Step Rebranding Guide (For Your Fork)

### Step 1: Fork & Clone
1. Click **Fork** at the top right of this repository on GitHub.
2. Clone your newly created fork locally:
   ```bash
   git clone https://github.com/<your-username>/<your-repo-name>.git
   cd <your-repo-name>
   ```

### Step 2: Set Your Team in `config.py`
Open `cbj_sentinel/config.py`. Locate line 54:
```python
# Change this single variable to re-brand the app for any NHL team!
TEAM = os.environ.get("NHL_SENTINEL_TEAM", "CBJ").upper()
```
Replace `"CBJ"` with your team's 3-letter tri-code (e.g. `"NYR"`, `"TOR"`, `"COL"`):
```python
TEAM = os.environ.get("NHL_SENTINEL_TEAM", "NYR").upper()
```

That single change immediately re-keys:
- **Application Window Title & App ID** (e.g. `Rangers Gameday Sentinel`)
- **Division & Conference Standings** (Metropolitan, Atlantic, Central, or Pacific)
- **Official NHL API Endpoints** (Schedule, Club Stats, Roster, GameCenter)
- **ESPN Team News & NHL.com Forge News Feeds**
- **Team Subreddit Public Feed** (e.g. `r/rangers`)
- **Primary & Secondary Color Schemes** (Canvas rink, cards, accents, headers)
- **High-Res Team Logo** (downloaded automatically from ESPN CDN)

---

### Step 3: Custom Team Logos & Icons

1. **Automatic Logo Fetch (Default):**
   The application automatically downloads your team's official 500x500 crest from ESPN's CDN (`https://a.espncdn.com/i/teamlogos/nhl/500/{tricode}.png`) and caches it in `%APPDATA%\<AppId>\team_logo.png`.
2. **Bundled Offline Logo:**
   To bundle a crisp offline logo directly with the application, replace `cbj_sentinel/logo.png` with a 500x500 or 256x256 transparent PNG.
3. **Executable Windows Icon (`app.ico`):**
   To change the Windows `.exe` desktop icon:
   ```powershell
   py -c "from PIL import Image; Image.open('cbj_sentinel/logo.png').resize((256, 256)).save('app.ico', format='ICO', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])"
   ```

---

### Step 4: Custom Goal Horn & Sound Effects

1. **Procedural Fallback (Built-in):**
   If no audio files are provided, the app synthesizes a retro organ fanfare dynamically using Python's `wave` module.
2. **Team Goal Horn (`horn.wav`):**
   - Place your team's official goal horn WAV file at `cbj_sentinel/assets/horn.wav`.
   - Users can also drop a `custom_horn.wav` directly into their `%APPDATA%\<AppId>\` folder.
   - Recommended specs: 16-bit PCM WAV, 44.1 kHz or 48 kHz stereo, under 10 MB.

---

### Step 5: Custom News Sources & Local Broadcasters

In `cbj_sentinel/config.py`:

#### 1. News Feeds (`NEWS_SOURCES`)
Add your team's SB Nation blog, local newspapers, or YouTube channels:
```python
NEWS_SOURCES = (
    {"id": "nhl", "name": "NHL.com (official)", "kind": "forge",
     "url": f"https://forge-dapi.d3.nhle.com/v2/content/en-us/stories?tags.slug=teamid-{NHL_TEAM_ID}&context.slug=nhl&$limit=15"},
    {"id": "espn", "name": "ESPN", "kind": "espn",
     "url": f"https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/news?team={ESPN_TEAM_ID}&limit=15"},
    {"id": "reddit", "name": f"r/{_p['subreddit']}", "kind": "feed",
     "url": f"https://www.reddit.com/r/{_p['subreddit']}/.rss"},
    # Add your team's fan blogs or YouTube channels:
    {"id": "blog", "name": "Blueshirt Banter", "kind": "feed", "url": "https://www.blueshirtbanter.com/feed/"},
)
```
*Note: Any external domain added to `NEWS_SOURCES` must also be added to `FETCH_HOSTS` in `config.py` to satisfy the security sandbox.*

#### 2. Regional Sports Networks (`WATCH_OPTIONS`)
Update `WATCH_OPTIONS` in `cbj_sentinel/config.py` with your market's regional sports networks:
```python
WATCH_OPTIONS = {
    "regional": ("MSG+ / Sportsnet", "https://www.msgplus.tv/"),
    "espn": ("ESPN+ / NHL Power Play", "https://plus.espn.com/nhl"),
    "fubo": ("Fubo", "https://www.fubo.tv/"),
    "nhl": ("NHL.com Tune-In Guide", "https://www.nhl.com/info/how-to-watch"),
}
```

---

### Step 6: Updating GitHub Repository & Version Info

1. Update `GITHUB_REPO` in `cbj_sentinel/config.py`:
   ```python
   GITHUB_REPO = "<your-github-username>/<your-repo-name>"
   ```
2. Update metadata in `version_info.txt`:
   ```python
   StringStruct('CompanyName', 'Your Name / Org'),
   StringStruct('FileDescription', 'NYR Gameday Sentinel - Unofficial Rangers Desktop Tracker'),
   StringStruct('OriginalFilename', 'NYRGamedaySentinel.exe'),
   StringStruct('ProductName', 'NYR Gameday Sentinel'),
   ```
3. Update `CBJGamedaySentinel.spec` with your executable name if desired.

---

### Step 7: Compiling the Standalone Windows `.exe`

Run the included build script:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1
```
The compiled, portable standalone Windows executable will be generated in `dist/`.

---

## 📋 Complete 32-Team Master Reference Catalog

All 32 NHL franchises are pre-configured in `cbj_sentinel/config.py`:

| Tri-Code | Team Name | Division | Conf | NHL ID | ESPN ID | Primary Color | Secondary Color | Subreddit |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **ANA** | Anaheim Ducks | Pacific | West | 24 | 25 | `#F47A38` | `#B9975B` | `r/AnaheimDucks` |
| **BOS** | Boston Bruins | Atlantic | East | 6 | 1 | `#000000` | `#FFB81C` | `r/BostonBruins` |
| **BUF** | Buffalo Sabres | Atlantic | East | 7 | 2 | `#002654` | `#FCB514` | `r/sabres` |
| **CAR** | Carolina Hurricanes | Metro | East | 12 | 7 | `#CC0000` | `#000000` | `r/canes` |
| **CBJ** | Columbus Blue Jackets | Metro | East | 29 | 29 | `#041E42` | `#C8102E` | `r/BlueJackets` |
| **CGY** | Calgary Flames | Pacific | West | 20 | 3 | `#C8102E` | `#F1BE48` | `r/CalgaryFlames` |
| **CHI** | Chicago Blackhawks | Central | West | 16 | 4 | `#CF0A2C` | `#000000` | `r/hawks` |
| **COL** | Colorado Avalanche | Central | West | 21 | 17 | `#6F263D` | `#236192` | `r/ColoradoAvalanche` |
| **DAL** | Dallas Stars | Central | West | 25 | 6 | `#006847` | `#8F8F8C` | `r/DallasStars` |
| **DET** | Detroit Red Wings | Atlantic | East | 17 | 5 | `#CE1126` | `#FFFFFF` | `r/DetroitRedWings` |
| **EDM** | Edmonton Oilers | Pacific | West | 22 | 8 | `#041E42` | `#FF4C00` | `r/EdmontonOilers` |
| **FLA** | Florida Panthers | Atlantic | East | 13 | 26 | `#041E42` | `#C8102E` | `r/FloridaPanthers` |
| **LAK** | Los Angeles Kings | Pacific | West | 26 | 9 | `#111111` | `#A2AAAD` | `r/losangeleskings` |
| **MIN** | Minnesota Wild | Central | West | 30 | 30 | `#154734` | `#A6192E` | `r/wildhockey` |
| **MTL** | Montreal Canadiens | Atlantic | East | 8 | 10 | `#AF1E2D` | `#192168` | `r/Habs` |
| **NJD** | New Jersey Devils | Metro | East | 1 | 11 | `#CE1126` | `#000000` | `r/devils` |
| **NSH** | Nashville Predators | Central | West | 18 | 27 | `#FFB81C` | `#041E42` | `r/Predators` |
| **NYI** | New York Islanders | Metro | East | 2 | 12 | `#00539B` | `#F47920` | `r/NewYorkIslanders` |
| **NYR** | New York Rangers | Metro | East | 3 | 13 | `#0038A8` | `#CE1126` | `r/rangers` |
| **OTT** | Ottawa Senators | Atlantic | East | 9 | 14 | `#C8102E` | `#000000` | `r/ottawasensors` |
| **PHI** | Philadelphia Flyers | Metro | East | 4 | 15 | `#F74902` | `#000000` | `r/Flyers` |
| **PIT** | Pittsburgh Penguins | Metro | East | 5 | 16 | `#000000` | `#FCB514` | `r/penguins` |
| **SEA** | Seattle Kraken | Pacific | West | 55 | 124292 | `#001628` | `#99D9D9` | `r/SeattleKraken` |
| **SJS** | San Jose Sharks | Pacific | West | 28 | 18 | `#006D75` | `#EA7200` | `r/SanJoseSharks` |
| **STL** | St. Louis Blues | Central | West | 19 | 19 | `#002F87` | `#FCB514` | `r/stlouisblues` |
| **TBL** | Tampa Bay Lightning | Atlantic | East | 14 | 20 | `#002868` | `#FFFFFF` | `r/TampaBayLightning` |
| **TOR** | Toronto Maple Leafs | Atlantic | East | 10 | 21 | `#00205B` | `#FFFFFF` | `r/leafs` |
| **UTA** | Utah Hockey Club | Central | West | 59 | 140656 | `#010101` | `#69B3E7` | `r/Utah_Hockey` |
| **VAN** | Vancouver Canucks | Pacific | West | 23 | 22 | `#00205B` | `#00843D` | `r/canucks` |
| **VGK** | Vegas Golden Knights | Pacific | West | 54 | 37 | `#B4975A` | `#333F48` | `r/goldenknights` |
| **WPG** | Winnipeg Jets | Central | West | 52 | 28 | `#041E42` | `#004C97` | `r/winnipegjets` |
| **WSH** | Washington Capitals | Metro | East | 15 | 23 | `#041E42` | `#C8102E` | `r/capitals` |

---

## 🔒 Security Invariants & Guardrails

When publishing a fork, ensure the security invariants in `SECURITY.md` and `cbj_sentinel/net.py` are preserved:
- **HTTPS Only**: All network connections require valid HTTPS.
- **Strict Host Allowlists**: Never allow un-vetted domains in `FETCH_HOSTS` or `BROWSER_HOSTS`.
- **Zero Local Shell Execution**: Stream and video links must always open via `webbrowser.open` through validated HTTP/HTTPS schemes to prevent arbitrary file launch vulnerabilities.
- **Response Size Caps**: All network payloads are bounded (`MAX_JSON_BYTES`, `MAX_FEED_BYTES`, `MAX_IMAGE_BYTES`).
