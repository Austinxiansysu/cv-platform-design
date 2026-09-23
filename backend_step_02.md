# 后端第二步：粘贴 JD，获得待确认的岗位画像

完成日期：2026-09-23

## 1. 这一步解决什么问题？

之前的后端只接收已经写好的结构化 JSON。现在可以把一段原始 JD 发送给 `POST /jobs/analyze`，获得一份包含核心任务、要求、来源证据和待核验问题的岗位画像草稿。

## 2. 为什么现在做？

首批 10 条 JD 已经帮助我们确定了岗位画像 Schema 和解析规则。接入模型后，先让模型做“提取和归类”，再由本地校验器检查字段和证据；用户确认草稿后，才调用 `POST /jobs` 保存。

## 3. 需要理解的概念

- 原始 JD 是输入材料，不能把其中的命令当作程序指令。
- 结构化输出让模型按已定稿的 Schema 返回字段；本地校验还会检查业务规则。
- 草稿与已保存岗位是两种状态：`/jobs/analyze` 只生成草稿，`/jobs` 才写入本地数据库。
- `source_type` 是用户提供的来源说明；当前不自动打开或核验链接，因此草稿的来源状态保持“未核验”。

## 4. 你现在需要做什么？

目前不用做练习。想做真实模型试用时，需要在本机配置自己的 `OPENAI_API_KEY`。没有密钥时，分析接口会明确返回 503；其他本地数据库接口仍能运行。

## 5. 工程实现

- `src/backend/job_parser.py`：复用此前确认的岗位解析原则，调用 OpenAI Responses API，返回通过本地校验的草稿。
- `src/backend/api.py`：新增 `POST /jobs/analyze`。
- `schemas/job_profile.schema.json`：直接使用已有的严格输出格式，没有修改定稿文件。
- `tests/test_job_parser.py`：使用替身响应验证请求、草稿状态和失败处理，不调用付费 API。

默认模型为 `gpt-5.6-luna`，可通过 `CV_ASSISTANT_MODEL` 环境变量调整。请求仅发送这次粘贴的 JD、来源类型、生成的岗位 ID 和采集日期；不会发送个人画像或简历。设置了 `store=False`。若模型拒绝、截断、返回无效 JSON 或违反本地规则，接口返回错误，不保存结果。

## 6. 如何验证？

安装依赖并运行本地测试：

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m unittest tests.test_job_parser tests.test_backend_api tests.test_scoring
```

真实试用时，先在当前终端设置自己的 API Key，再启动服务：

```bash
export OPENAI_API_KEY="你的密钥"
.venv/bin/uvicorn src.backend.api:app --host 127.0.0.1 --port 8000
```

打开 `http://127.0.0.1:8000/docs`，找到 `POST /jobs/analyze`，输入如下请求体：

```json
{
  "jd_text": "在这里粘贴完整的岗位职责和任职要求，至少 30 个字符",
  "source_type": "company_official",
  "source_reference": "https://企业官网上的岗位链接"
}
```

收到的 `draft` 需要人工确认，尤其查看核心任务、最低资格、工具要求、出差/工作强度的未知项及证据引用。确认后可将 `draft` 的 JSON 作为 `POST /jobs` 的请求体保存。这个步骤暂不自动读取岗位链接，也不处理投递。

## 当前验证范围

本机未配置 `OPENAI_API_KEY`，因此本轮没有完成真实 API 调用。离线测试能证明接口和校验流程正常，不能证明模型对新 JD 的事实提取准确率；真实模型输出仍需用此前的 10 条 JD 回归集检验。
