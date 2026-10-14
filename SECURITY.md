# Security Policy (CBJ Gameday Sentinel v2.0 - Tauri / Rust)

## Zero-Trust Architecture & Hardening

**CBJ Gameday Sentinel v2.0** is built on Tauri v2 + Rust with strict isolation between the frontend WebView and the native OS layer:

1. **Strict Network Host Allowlist & SSRF Defense (`is_allowed_api_host`):**
   - Read-only `HTTPS` requests (`--proto =https`, `--proto-redir =https`) are restricted exclusively to an explicit domain allowlist:
     - `api-web.nhle.com`, `assets.nhle.com`, `wsr.nhle.com`, `*.nhle.com`, `*.d3.nhle.com` (Official NHL APIs & headshots)
     - `*.espn.com`, `*.espncdn.com` (ESPN NHL news & logos)
     - `*.reddit.com` (Subreddit community feeds)
     - `api.github.com` (Release checks)
   - Loopback (`localhost`, `127.0.0.1`, `::1`), link-local (`169.254.*`), and RFC1918 private LAN subnets (`192.168.*`, `10.*`, `172.16-31.*`) are strictly blocked.

2. **CWE-88 Argument Injection Immunity:**
   - The native proxy command passes the POSIX/Windows `"--"` operand terminator directly before the validated URL so inputs starting with `-` can never be interpreted as CLI flags.

3. **Resource & Payload Bounds:**
   - Network responses are capped at **15 MB** (`--max-filesize 15728640`) with a **15-second** timeout (`--max-time 15`).

4. **External Browser Link Allowlist (`is_allowed_external_url`):**
   - External links opened via `open_external_url` must use `https://` and match approved domains (`nhl.com`, `espn.com`, `amazon.com`, `reddit.com`, `youtube.com`, `github.com`).

5. **Atomic Settings Persistence:**
   - User settings are stored in `%APPDATA%\CBJGamedaySentinel\settings.json`, capped at **64 KB**, validated as JSON objects prior to write, and committed atomically via `.tmp` write-and-rename.

6. **Windows Startup Registry Sanitization:**
   - When *Start with Windows* is enabled, the executable path written to `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` is verified on disk and sanitized against quote or newline injection.

7. **Content Security Policy (CSP):**
   - Enforced in `src-tauri/tauri.conf.json`, restricting scripts, styles, images, and connections strictly to `'self'` and approved NHL/ESPN/GitHub endpoints.

## Reporting a Vulnerability

Please open a private security advisory on GitHub (**Security → Report a vulnerability**) rather than a public issue.

## Verifying Downloads

Every GitHub Release includes a `.sha256` checksum file. Verify your download with PowerShell:

```powershell
Get-FileHash .\CBJGamedaySentinel.exe -Algorithm SHA256
```
