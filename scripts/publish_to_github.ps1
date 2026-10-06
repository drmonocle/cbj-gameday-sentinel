$ErrorActionPreference = "Stop"
$env:PATH = "C:\Program Files\Git\cmd;C:\Program Files\GitHub CLI;$env:PATH"

Write-Host "Checking GitHub authentication..." -ForegroundColor Cyan
$auth = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Logging into GitHub via browser..." -ForegroundColor Yellow
    gh auth login --web -h github.com -p https
}

Write-Host "Checking / creating repository drmonocle/cbj-gameday-sentinel..." -ForegroundColor Cyan
$view = gh repo view drmonocle/cbj-gameday-sentinel 2>&1
if ($LASTEXITCODE -ne 0) {
    gh repo create drmonocle/cbj-gameday-sentinel --public --source=. --remote=origin --push
} else {
    git push -u origin main
}

Write-Host "Successfully published! View your repo at: https://github.com/drmonocle/cbj-gameday-sentinel" -ForegroundColor Green
