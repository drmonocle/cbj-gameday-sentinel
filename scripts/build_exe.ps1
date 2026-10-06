# Builds a single-file Windows executable for GitHub Releases.
# Usage (from repo root):  powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1
$ErrorActionPreference = "Stop"
py -m pip install --upgrade pyinstaller -r requirements.txt
py -m pytest -q
py -m PyInstaller --noconfirm --onefile --windowed --name CBJGamedaySentinel run_sentinel.pyw
$exe = "dist\CBJGamedaySentinel.exe"
$hash = (Get-FileHash $exe -Algorithm SHA256).Hash
"$hash  CBJGamedaySentinel.exe" | Out-File -Encoding ascii "dist\SHA256SUMS.txt"
Write-Host "Built $exe"
Write-Host "SHA-256: $hash  (paste this into the release notes)"
