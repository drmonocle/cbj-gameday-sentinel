# Security Policy

## What the app does (and doesn't do)

- **Network:** Read-only HTTPS `GET` requests, only to an exact-match host allowlist (`FETCH_HOSTS` in `cbj_sentinel/config.py`):
  - `api-web.nhle.com`: scores, schedule, stats, standings, roster, players
  - `forge-dapi.d3.nhle.com`: official NHL.com news
  - `assets.nhle.com`: player headshots
  - `site.api.espn.com`: ESPN news
  - `a.espncdn.com`: the team logo image (validated, re-encoded, and cached locally; refreshed every 30 days)
  - `www.jacketscannon.com`, `www.1stohiobattery.com`, `www.reddit.com`, `www.youtube.com`: public RSS/Atom feeds
  - `api.github.com`: optional once-a-day release check (only if the maintainer sets `GITHUB_REPO`)

  The app refuses any other host, plain `http`, non-443 ports, credentials in URLs, or a redirect to an unlisted host.
- **No accounts, API keys, telemetry, analytics, or tracking.** Nothing about you leaves your computer except normal HTTP requests carrying a `User-Agent` that names the app.
- **Browser links:** Opened only if they are `https` and on a separate allowlist (`BROWSER_HOSTS`): NHL, Amazon/Prime Video, ESPN, Fubo, the news sites above, YouTube, and GitHub. Lookalikes such as `www.nhl.com.evil.com` are rejected. This stops a tampered feed from launching local files, UNC paths, or other programs. It matters because on Windows, Python's `webbrowser.open` hands strings to `os.startfile`. NHL.com news links are built from a slug that must match `[a-z0-9-]`.
- **Parsing untrusted data:**
  - RSS/Atom containing a DTD or entity declarations is rejected, which prevents "billion laughs" entity expansion.
  - All text is unescaped, stripped of tags and control characters, and length-capped.
  - Responses are capped (5 MB JSON / 3 MB feeds / 2 MB images) and time out.
  - Images must be PNG/JPEG/WEBP, are dimension-checked (≤ 4 MP) before decoding. Player headshots are never written to disk; the team logo is re-encoded and cached (see below).
- **Custom horn import:** Only PCM `.wav` files of ≤ 10 MB and ≤ 30 s are accepted. They are validated with Python's `wave` module and copied into the app data folder. Playback uses the Windows `PlaySound` API, and no external player is launched.
- **Settings file:** Loaded with strict type checks and value clamping. A corrupt or tampered `settings.json` falls back to defaults.
- **Writes to disk:** Only inside `%APPDATA%\CBJGamedaySentinel\`:
  - `settings.json`
  - `sentinel.log`
  - the generated `goal_horn_v2.wav` / `opponent_chime_v1.wav`, and volume-scaled `_play_*.wav` copies of them
  - `team_logo.png` (the re-encoded team logo downloaded from ESPN)
  - an optional `custom_horn.wav` and an optional user-supplied `custom_logo.png`

  If you enable *Start with Windows*, one per-user value is written to `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`. No admin rights are requested.
- **No shell commands, `eval`, or dynamic code loading.** All UI updates happen on the Tk main thread.

## Reporting a vulnerability

Please open a private security advisory on GitHub (**Security → Report a vulnerability**) rather than a public issue. Include steps to reproduce and the version shown on the Settings tab.

## Verifying downloads

Release `.exe` files are unsigned. Each release lists a SHA-256 hash. Check it with:

```powershell
Get-FileHash .\CBJGamedaySentinel.exe -Algorithm SHA256
```

If you'd rather not run an unsigned binary, run from source (see README).
