# CBJ Gameday Sentinel

An unofficial, lightweight Windows system-tray app for Columbus Blue Jackets fans. It sits quietly by your clock and comes alive on gameday.

> **Unofficial fan project.** Not affiliated with, endorsed by, or sponsored by the Columbus Blue Jackets or the National Hockey League. The Blue Jackets name and logo are trademarks of the club and are shown only to identify the team. The logo is not stored in this repository; the app downloads it at runtime for display. No arena audio is included. Rights holders: open an issue and it will be removed promptly.

## Features

**Gameday**
- **Live tab**: who CBJ is playing and where (full opponent name, arena, city, local puck-drop time, TV networks), with a live countdown and a one-click game preview / GameCenter link.
- **During games**: score, period and clock, shots, **power-play and goalie-pulled alerts**, a running scoring summary (PPG/SHG/EN tags), and a penalty log.
- **Goal horn with volume slider**: an original synthesized horn-and-cannon tuned to sound like the arena. You can import your own `.wav` instead, and turn on a soft chime for opponent goals.
- **Windows notifications**: goals, end of each period, final score, and a 30-minute puck-drop reminder.
- **Mini scoreboard**: a small always-on-top overlay you can drag anywhere. Double-click it to open the app, or click ✕ to dismiss it for the night.
- **Live score in the tray icon**: the ring turns green when CBJ leads and red when they trail.
- **Stream delay**: hold back scores, horn, and alerts by 0–180 s so a lagging stream doesn't get spoiled.
- **Spoiler mode** (one click in the header): hides final scores, results, records, standings, and headlines until you click *Reveal*. Made for watching a replay later.
- **Watch button**: opens Prime Video (Blue Jackets Hockey Network), ESPN+, Fubo, or the NHL where-to-watch page. You pick which in Settings.

**Between games**
- **Games**: regular-season, preseason, and playoff records (W-L-OTL, goals for/against, differential); the next 10 games with venue and TV; recent results with three stars, scoring, and penalties; team scoring leaders.
- **Standings**: the Metropolitan Division, Eastern Conference division leaders, and the wild-card race with the playoff cut line marked.
- **News & Media**: merged headlines and videos from NHL.com, ESPN, The Cannon, 1st Ohio Battery, r/BlueJackets, and YouTube (official Blue Jackets, Locked On CBJ, and NHL highlights), with quick source filters and direct VOD links.
- **Roster & player cards**: click any player for a headshot, bio, draft info, season and career stats, and the last 5 games.
- Sharp text on high-DPI displays, and a tray menu for everything.

## Install

### Option A: Download the app (no Python needed)
1. Get `CBJGamedaySentinel.exe` from the [Releases](https://github.com/drmonocle/cbj-gameday-sentinel/releases) page.
2. Optional: check that `Get-FileHash .\CBJGamedaySentinel.exe` matches the SHA-256 listed in the release notes.
3. Double-click it. Windows SmartScreen may warn because the exe is unsigned. Click **More info → Run anyway**, or use Option B.

### Option B: Run from source
Requires Windows 10/11 and [Python 3.9+](https://www.python.org/downloads/).
```powershell
git clone https://github.com/drmonocle/cbj-gameday-sentinel.git
cd cbj-gameday-sentinel
python -m pip install -r requirements.txt
pythonw run_sentinel.pyw
```
To launch it automatically, open **⚙ Settings** and check **Start minimized to tray when Windows starts**.

## Using your own goal horn
**⚙ Settings → Goal horn → Use my own horn…** accepts a 16-bit PCM `.wav` up to 30 seconds and 10 MB. The file is copied into `%APPDATA%\CBJGamedaySentinel\custom_horn.wav` and never leaves your PC. Only use audio you have the right to use.

## Privacy & security
The app only makes read-only HTTPS requests to an allowlist of public sources (listed below). It has no accounts, telemetry, or tracking. See [SECURITY.md](SECURITY.md) for the full model.

Files are stored in `%APPDATA%\CBJGamedaySentinel\`. To uninstall, untick *Start with Windows*, exit from the tray, and delete that folder.

## Data sources
- **NHL** (`api-web.nhle.com`, `forge-dapi.d3.nhle.com`, `assets.nhle.com`): scores, schedule, stats, standings, roster, player cards, headshots, and official news. These public endpoints are undocumented and may change without notice. If something breaks, please open an issue. Records are computed from final scores, and they match NHL.com standings, including the convention that a shootout win counts as one goal.
- **ESPN** (`site.api.espn.com`, `a.espncdn.com`): team news and the team logo image.
- **The Cannon**, **1st Ohio Battery**, **r/BlueJackets**: public RSS/Atom feeds. Articles open on the original sites.
- **YouTube** (`www.youtube.com`): public Atom video feeds for official CBJ channel, Locked On CBJ, and NHL highlights. Clicking a video opens the VOD directly in your browser.

## Development
```powershell
python -m pip install -r requirements.txt pytest
python -m pytest
python -m cbj_sentinel        # run with a console for debugging
```
Logs are written to `%APPDATA%\CBJGamedaySentinel\sentinel.log`. The in-app "update available" check reads the latest GitHub Release of `drmonocle/cbj-gameday-sentinel` once a day (`GITHUB_REPO` in `cbj_sentinel/config.py`).

To build a release: `powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1`

## License
Code: MIT. See [LICENSE](LICENSE). The MIT license covers this project's code only, not team names, logos, or NHL data.
