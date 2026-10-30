#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  echo "未找到 .venv。请先执行："
  echo "  python3 -m venv .venv"
  echo "  .venv/bin/pip install -r requirements.txt"
  exit 1
fi

if [ ! -f "frontend/dist/index.html" ]; then
  echo "前端尚未构建：cd frontend && pnpm install && pnpm build"
fi

export PYTHONPATH="$PWD/backend"
echo "学业罗盘启动中： http://127.0.0.1:8000"
echo "学生演示：2023001 / 123456    管理员：admin / 123456"
exec .venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
