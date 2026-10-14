# 🏒 CBJ Gameday Sentinel (v2.0 - Tauri / Rust Stack)

An ultra-lightweight, high-performance desktop companion for **Columbus Blue Jackets** fans (and interchangeable for all **32 NHL franchises**). Built on the modern **Tauri v2 + Rust + React 19 + TypeScript + Vite + Tailwind CSS** architecture.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Binary Size](https://img.shields.io/badge/binary-<4_MB-emerald.svg)
![Memory](https://img.shields.io/badge/RAM-<40_MB-cyan.svg)
![Framework](https://img.shields.io/badge/Tauri-v2-purple.svg)

---

## ⚡ Why Tauri v2 + Rust (vs. Legacy Python / Tkinter)?

| Metric | Legacy Python / Tkinter | Tauri v2 + Rust (Sentinel v2.0) |
| :--- | :--- | :--- |
| **Executable Size** | ~60 – 75 MB (bloated PyInstaller bundle) | **~3.8 MB** (standalone native binary) |
| **Idle Memory (RAM)** | ~75 – 90 MB | **< 40 MB** (via native WebView2) |
| **Cold-Start Time** | 2.5 – 3.5s (unpacking `%TEMP%`) | **< 100 ms** (instantaneous) |
| **Shot Chart & Ice Rink**| Static Tkinter canvas | **Interactive SVG Regulation Rink** with hover tooltips, player headshots, shot distances, and High Danger Slot detection |
| **Goal Horn & Cannon** | Fragile OS audio thread | **Web Audio Synthesizer** (138 Hz Nationwide Arena harmonics + deep cannon blast reverb) |
| **Settings Persistence**| Ad-hoc config | **Permanent `%APPDATA%\CBJGamedaySentinel\settings.json`** via Rust backend |
| **System Tray** | Python pystray thread crashes | **Rock-solid native Win32 system tray** with single-instance named mutex |

---

## 🚀 Key Features

1. **Live Gameday Scoreboard & Automatic Next-Game Rollover:**
   - Real-time score ticker, period clock, and intermission countdowns.
   - Power Play situation badges (e.g. `PP CBJ 5-on-4 (1:23)`) and Empty Net tracking.
   - US TV network listings (Prime Video, FDSN OH, ESPN+, ABC, TNT) with a 1-click **Watch Stream** button.
   - Chronological scoring summary with player mugshots, PPG/SHG/EN badges, and 1-click **▶ Replay** video buttons.
   - Three Stars of the Game selection.
   - **Smart 3-Hour Post-Game Rollover:** Keeps the final score, scoring summary, and Three Stars on screen for ~3 hours after the final horn, then automatically transitions to the **Next Scheduled Game** featuring a live countdown badge (`In 3d 10h`), team season records, a side-by-side **Matchup Tale of the Tape**, and an **Upcoming 4-Game Schedule Horizon**.

2. **Interactive SVG Regulation Half-Rink Shot Chart:**
   - **Player Headshot Goal Markers:** Goals are plotted directly on the ice using circular official NHL player headshots with golden team halos, jersey number badges (`#78`, `#24`), and surname pills.
   - **Game Selector:** Choose between **Current / Live Game**, **Past Recent Games**, or **All Season Games Combined (Heatmap)**.
   - **Game Banner:** Clear header showing matchup, date, final score, and venue so you always know which game is on screen.
   - **High Danger Chances (HDC):** Real-time slot threat calculation ($\le 22\text{ ft}$, $|y| \le 12\text{ ft}$) with a dedicated **Slot High Danger** filter.
   - **Interactive Hover HUD:** Hover over any shot or goal to view shooter mugshot, jersey number, shot type (wrist, slap, backhand, tip-in), distance in feet, time, and assists.
   - **Independent Filters:**
     - Team: `Both` / `CBJ Only` / `Opponent`
     - Type: `All` / `SOG` / `★ Goals` / `Missed/Blocked`
     - Danger: `All Shots` / `Slot High Danger`
     - Period: `All` / `P1` / `P2` / `P3` / `OT`

3. **Arena Goal Horn & Cannon Blast:**
   - Procedural Web Audio synthesizer modeled on Nationwide Arena's 138 Hz fundamental frequency and 20 measured harmonics.
   - Followed by the thunderous boom of the Civil War replica cannon with sub-bass thump and acoustic reverb.
   - Test Goal Horn button, volume slider (0-100%), and optional chime for opponent goals.

4. **Multi-Source News Feed:**
   - Aggregates stories from official **NHL.com**, **ESPN**, and community feeds.
   - Relative publication time ("5m ago", "2h ago"), summaries, and direct article browser launcher.

5. **Active Roster & Player Bio Cards:**
   - Forwards, Defensemen, and Goalies organized by sweater number.
   - Click any player to open their **Player Bio Card** showing headshot, age, height, weight, birthplace, draft status, season statistics, career totals, and recent games log.

6. **Standings & Playoff Race:**
   - Division standings, Conference leaders, and Wildcard race with playoff cutoff lines.
   - Tracks GP, W, L, OTL, PTS, Point Percentage, Goal Differential, Last 10, and active Streaks.

7. **Native Windows Integration:**
   - Win32 single-instance named mutex (`Local\CBJGamedaySentinelSingleInstance`).
   - Native Windows toast notifications on goals and period endings.
   - Start with Windows registry integration (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`).
   - Minimize-to-tray on close option.
   - Permanent settings persistence in `%APPDATA%\CBJGamedaySentinel\settings.json`.

---

## 🎨 Universal 32-Team Forkability (GitHub Friendly)

Want to fork this app for the **Toronto Maple Leafs**, **New York Rangers**, or **Seattle Kraken**?

You can switch your team in two ways:
1. **In-App:** Open the **Settings** tab and pick any of the 32 NHL franchises from the dropdown. The theme, colors, logos, and API queries update immediately.
2. **Hardcode for Distribution:** In `src/config/teams.ts`, change:
   ```ts
   export const DEFAULT_TEAM = "TOR"; // or "NYR", "SEA", "EDM", etc.
   ```
The entire application will rebrand itself automatically!

---

## 🛠️ Building & Packaging

### Prerequisites
- [Node.js](https://nodejs.org/) (v20+ recommended)
- [Rust](https://rustup.rs/) (v1.80+)
- Visual Studio 2022 C++ Build Tools (with Windows 10/11 SDK)

### Quick Start (Dev Mode)
```powershell
# Install frontend dependencies
npm.cmd install

# Start Vite and Tauri in live development mode
npm.cmd run tauri dev
```

### Packaging Release Binary
Run the automated packaging script:
```powershell
.\scripts\package_release.ps1
```
This builds the optimized release binary in `release\CBJGamedaySentinel.exe` and computes its official `CBJGamedaySentinel.exe.sha256` checksum.

---

## 📄 License & Publisher
- **Publisher:** Monocle Productions LLC
- **License:** MIT License
- All NHL logos and team names are trademarks of the National Hockey League and their respective clubs.
