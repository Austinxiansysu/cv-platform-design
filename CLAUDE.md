# CV Platform Design

## 项目说明

AI 简历匹配平台：输入 JD 和候选人简历，输出结构化匹配评分和对齐分析。

## 项目结构

- `src/matching/scoring.py` — 核心匹配评分逻辑
- `schemas/` — JSON Schema 定义，已定稿，不要修改
- `tests/` — 回归测试，不要删除测试数据
- `eval_inputs/` — 评测输入 prompt 模板
- `fixtures/` — 评测期望输出

## Git 提交规范

- 每次改动后执行 `git add . && git commit -m "描述"`
- commit message 用中文
- 不要提交 `eval_outputs/` 和 `eval_runs/`（已在 .gitignore 排除）
- 改完推送到远程：`git push`

## 禁止事项

- 不要修改 `schemas/` 下已定稿的 schema 文件
- 不要删除 `tests/` 下的回归测试用例
