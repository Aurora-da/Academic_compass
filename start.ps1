$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "未找到 .venv。请先执行：" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv" -ForegroundColor Cyan
    Write-Host "  .\.venv\Scripts\python.exe -m pip install -r requirements.txt" -ForegroundColor Cyan
    exit 1
}

if (-not (Test-Path (Join-Path $root "frontend\dist\index.html"))) {
    Write-Host "前端尚未构建：cd frontend; pnpm install --node-linker=hoisted; pnpm build" -ForegroundColor Yellow
}

$env:PYTHONPATH = Join-Path $root "backend"
Write-Host "学业罗盘启动中： http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "学生演示：2023001 / 123456    管理员：admin / 123456" -ForegroundColor DarkGray

Start-Job -ScriptBlock {
    Start-Sleep -Seconds 4
    Start-Process "http://127.0.0.1:8000"
} | Out-Null

& $python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
