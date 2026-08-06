$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$managePath = Join-Path $projectRoot "manage.py"

if (-not (Test-Path -LiteralPath $managePath)) {
    throw "manage.py를 찾을 수 없습니다: $managePath"
}

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw ".venv가 없습니다. 먼저 Python으로 'python -m venv .venv'를 실행하고 requirements.txt를 설치하세요."
}

Set-Location -LiteralPath $projectRoot
$env:DJANGO_SETTINGS_MODULE = "config.settings.local"

& $pythonPath manage.py check
& $pythonPath manage.py migrate
& $pythonPath manage.py runserver 127.0.0.1:8000
