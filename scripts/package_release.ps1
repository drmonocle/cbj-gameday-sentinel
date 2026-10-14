# Package release script for CBJ Gameday Sentinel (Tauri v2)
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir
$srcTauriDir = Join-Path $rootDir "src-tauri"
$releaseDir = Join-Path $rootDir "release"

Write-Host "==> [1/4] Building React 19 Frontend..." -ForegroundColor Cyan
Set-Location $rootDir
cmd.exe /c "npm run build"
if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }

Write-Host "==> [2/4] Compiling Rust Release Binary with MSVC..." -ForegroundColor Cyan
Set-Location $srcTauriDir
cmd.exe /c 'call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" && set "PATH=%USERPROFILE%\.cargo\bin;%PATH%" && cargo build --release'
if ($LASTEXITCODE -ne 0) { throw "Rust release build failed" }

Write-Host "==> [3/4] Copying and packaging executable..." -ForegroundColor Cyan
$targetExe = Join-Path $srcTauriDir "target\release\cbj-sentinel-tauri.exe"
if (-not (Test-Path $targetExe)) {
    throw "Target executable not found at $targetExe"
}

$destExe = Join-Path $releaseDir "CBJGamedaySentinel.exe"
Copy-Item $targetExe $destExe -Force

$fileSizeMB = [math]::Round(((Get-Item $destExe).Length / 1MB), 2)
Write-Host "Release binary created: $destExe ($fileSizeMB MB)" -ForegroundColor Green

Write-Host "==> [4/4] Generating SHA-256 checksum..." -ForegroundColor Cyan
$hash = (Get-FileHash -Path $destExe -Algorithm SHA256).Hash.ToLower()
$shaFile = Join-Path $releaseDir "CBJGamedaySentinel.exe.sha256"
"$hash  CBJGamedaySentinel.exe" | Set-Content -Path $shaFile -Encoding ASCII

Write-Host "Checksum: $hash" -ForegroundColor Yellow

$zipFile = Join-Path $releaseDir "CBJGamedaySentinel_v2.0.0_windows_x64.zip"
Compress-Archive -Path $destExe -DestinationPath $zipFile -Force
Write-Host "Zip archive created: $zipFile" -ForegroundColor Green

Write-Host "==> Release packaging complete!" -ForegroundColor Cyan
