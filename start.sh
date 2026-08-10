#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
    kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo -e "\033[36m=== AI数字智育系统 启动脚本 ===\033[0m"

if [ ! -f "$ROOT/data/school.db" ]; then
    echo -e "\033[33m>>> 生成模拟数据...\033[0m"
    python "$ROOT/data/raw_data_gen.py"
    echo -e "\033[32m数据生成完成\033[0m"
else
    echo -e "\033[90m>>> 跳过数据生成\033[0m"
fi

echo -e "\033[33m>>> 启动后端 (端口 8000)...\033[0m"
(cd "$ROOT" && uvicorn backend.app:app --host 127.0.0.1 --port 8000) &
BACKEND_PID=$!

echo -n "等待后端就绪..."
READY=0
for i in $(seq 1 60); do
    if curl -sf --max-time 1 http://127.0.0.1:8000/ > /dev/null 2>&1; then
        READY=1
        break
    fi
    echo -n "."
    sleep 1
done
if [ "$READY" != "1" ]; then
    echo ""
    echo -e "\033[31m后端 60 秒内未就绪，已退出！\033[0m"
    exit 1
fi
echo -e " \033[32mOK\033[0m"

echo -e "\033[33m>>> 启动前端 (端口 3000)...\033[0m"
cd "$ROOT/frontend" && npm run dev
