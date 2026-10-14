# 🏒 Forking & Customizing for Any of the 32 NHL Teams

**CBJ Gameday Sentinel v2.0** includes a built-in **32-Team NHL Engine** (`src/config/teams.ts`), making it effortless to switch teams in-app or fork and rebrand for any NHL franchise.

---

## ⚡ Option 1: Switch Teams Directly In-App (Zero Code)

Open **CBJ Gameday Sentinel** and select any of the **32 NHL franchises** from the team dropdown in the top header or in the **Settings** tab.
Your selection is saved permanently to `%APPDATA%\CBJGamedaySentinel\settings.json` and immediately updates:
- Team logo, primary/secondary/accent colors, and header branding
- Live scoreboard, automatic 3-hour post-game rollover to the next scheduled game, and Matchup Tale of the Tape
- Regulation half-rink Shot Chart with player headshots for goals
- Division, Conference, and Wildcard standings highlights
- Active roster, player bio cards, and NHL.com / ESPN team news feeds

---

## 🚀 Option 2: Fork & Rebrand Your Own Default Build

1. **Fork & Clone** this repository on GitHub.
2. Open [`src/config/teams.ts`](src/config/teams.ts) and change the single `DEFAULT_TEAM` constant to your team's 3-letter NHL tri-code:
   ```ts
   export const DEFAULT_TEAM = "CBJ"; // e.g., "TOR", "NYR", "BOS", "EDM", "SEA", "FLA", etc.
   ```
3. *(Optional)* Update `"productName"` in [`src-tauri/tauri.conf.json`](src-tauri/tauri.conf.json) and replace the icons in `src-tauri/icons/`.
4. Run the release packager:
   ```powershell
   .\scripts\package_release.ps1
   ```
   Your standalone ~3.7 MB `.exe` and `.zip` bundle will be generated in `release\`.
