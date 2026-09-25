#!/bin/zsh

project_dir="${0:A:h}"
cd "$project_dir" || exit 1

if [[ ! -x .venv/bin/uvicorn || ! -x frontend/node_modules/.bin/vite ]]; then
  echo "依赖尚未安装。请先按 frontend/README.md 的说明安装后端和前端依赖。"
  read '?按回车关闭窗口…'
  exit 1
fi

if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1 || lsof -nP -iTCP:5173 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "本机 8000 或 5173 端口已被占用。请先关闭旧的实习路径启动窗口，再运行一次。"
  read '?按回车关闭窗口…'
  exit 1
fi

echo "正在启动实习路径…"
.venv/bin/uvicorn src.backend.api:app --host 127.0.0.1 --port 8000 &
backend_pid=$!
frontend/node_modules/.bin/vite frontend --host 127.0.0.1 --port 5173 --strictPort &
frontend_pid=$!

cleanup() {
  kill "$backend_pid" "$frontend_pid" 2>/dev/null
}
trap cleanup EXIT HUP INT TERM

sleep 2
if command -v open >/dev/null 2>&1; then
  open http://127.0.0.1:5173/
fi
echo "页面地址：http://127.0.0.1:5173/"
echo "请保持这个窗口开启；按 Control-C 停止服务。停止后需重新输入 DeepSeek Key。"
wait
