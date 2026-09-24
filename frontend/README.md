# 实习路径：本机页面

这是 React + Vite 单页界面，连接项目根目录的 FastAPI 后端。页面依次完成个人画像、岗位解读、匹配判断和求职记录。

在项目根目录启动后端：

```bash
.venv/bin/uvicorn src.backend.api:app --host 127.0.0.1 --port 8000
```

在 `frontend/` 目录启动页面：

```bash
npm install
npm run dev -- --host 127.0.0.1
```

打开 `http://127.0.0.1:5173/`。开发服务器把 `/api` 转发到本机后端，页面代码不包含模型 API Key。

模型分析需要在启动后端的终端设置 `DEEPSEEK_API_KEY`。用户勾选同意后，脱敏的简历文字或结构化画像才会发给所选模型服务商。分析草稿要由用户核对并确认，之后才保存到本地 SQLite；没有自动投递。
