# 后端第一步：让分析结果保存在本地

完成日期：2026-09-23

## 1. 这一步在产品中解决什么问题？

之前的个人画像、岗位画像和匹配结果只是文件，关闭程序后不方便查找和关联。现在它们能保存在本地 SQLite 数据库中。求职记录也可以按“收藏、计划、已投、面试、录用、拒绝、撤回”更新。

## 2. 为什么现在做？

10 条 JD 已经检验了画像字段和匹配逻辑。先固定“存什么”和“怎么读取”，后续前端才能稳定展示结果。这个版本直接保存已验证的结构化 JSON；已定稿的 `schemas/` 不变，计分仍使用 `src/matching/scoring.py`。

## 3. 你需要理解的概念

- **SQLite 数据库**：本地的一个文件，默认位于 `data/cv_assistant.sqlite3`。四张表分别存个人画像、岗位画像、匹配结果、投递记录。
- **API**：前端与后端之间的约定。例如 `POST /jobs` 提交岗位画像，`GET /jobs/JD-007` 读取它。
- **主键**：每条记录的唯一编号。这里分别是 `profile_version`、`job_id`、`match_id`、`application_id`。
- **关联**：匹配结果必须指向已经保存的个人画像和岗位；投递记录可关联岗位与匹配结果。
- **校验**：数据写入前检查字段、证据和任务引用。后端根据已有规则重新计分，不接受外部传入一个随意的总分。

## 4. 你自己先完成什么？

请画出四张表的关系，并用自己的话回答：为什么 `matches` 需要同时保存 `profile_version` 和 `job_id`？然后从十条样本中任选一条，看它的“职业方向”和“当前能否申请”为什么可能不同。这两件事属于产品与业务理解，不需要写代码。

## 5. 已由我完成的工程部分

- 本地数据库建表和记录读取：`src/backend/storage.py`；
- HTTP 接口和投递状态：`src/backend/api.py`；
- 已定稿 Schema、语义规则以及岗位任务对应关系校验：`src/backend/validation.py`；
- 使用真实夹具的端到端测试：`tests/test_backend_api.py`。

当前接口：

| 数据 | 写入 | 读取 | 其他 |
|---|---|---|---|
| 个人画像 | `POST /profiles` | `GET /profiles/{profile_version}` | 相同版本不可覆盖 |
| 岗位画像 | `POST /jobs` | `GET /jobs`、`GET /jobs/{job_id}` | 相同 ID 不可覆盖 |
| 匹配结果 | `POST /matches` | `GET /matches/{match_id}` | 创建时重新计算分数 |
| 求职记录 | `POST /applications` | `GET /applications`、`GET /applications/{id}` | `PATCH` 更新，`DELETE` 删除 |

画像和匹配结果按版本保留；修改后的内容应生成新版本或新匹配记录。求职记录属于不断变化的状态，可以直接更新。

## 6. 如何自己验证？

在项目目录执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m unittest tests.test_backend_api tests.test_scoring
.venv/bin/uvicorn src.backend.api:app --host 127.0.0.1 --port 8000
```

然后在本机打开 `http://127.0.0.1:8000/docs`，可看到所有接口并手动试用。测试用的是临时数据库，不会写入默认数据库。服务只绑定本机地址；默认数据库位于被 Git 忽略的 `data/`，不会随代码推送。

可先用 `fixtures/profile_expected.json`、`fixtures/fde_job_profile_expected.json`、`fixtures/fde_match_expected.json` 作为三个请求体，依次调用 `POST /profiles`、`POST /jobs`、`POST /matches`。同一个 ID 再次写入会得到 409；缺少字段或岗位任务未一一对齐会得到 422。

## 当前边界

这个阶段只接收已结构化的数据；还没有把原始简历或 JD 自动转换成这些字段，也没有前端页面。数据库保存在本机，但尚未加密；请不要把真实简历、手机号或邮箱放入公开仓库或共享测试文件。
