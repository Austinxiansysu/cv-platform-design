# AI 求职助手结构化输出 Schema

更新日期：2026-09-21

## 文件

- `profile.schema.json`：从简历、问卷和用户确认信息提取个人画像；
- `job_profile.schema.json`：从原始 JD 提取不依赖具体用户的岗位画像；
- `match_alignment.schema.json`：对个人画像和岗位画像进行逐项证据对齐，不计算最终分数。

## 设计约束

- 三份文件均使用严格结构化输出包装；
- 每个对象都设置 `additionalProperties: false`；
- 对象中的全部字段都列入 `required`；
- 可缺失信息使用 `null`、空数组或显式状态表达；
- unknown、not_demonstrated 和 confirmed_gap 分开；
- current_cycle_conflict 和 structural_conflict 分开；
- 原始职责 `tasks` 与用于匹配计分的 `task_clusters` 分开；
- 经验要求使用 `experience_requirements` 单独保存；
- 定性要求和机器可判断门槛通过 `gate_type` 分开；
- 最终分数和双结论由透明规则层计算，不由 AI 直接输出。

## 当前夹具

- `../fixtures/profile_expected.json`；
- `../fixtures/fde_job_profile_expected.json`；
- `../fixtures/tencent_business_analysis_job_profile_expected.json`；
- `../fixtures/fde_match_expected.json`；
- `../fixtures/tencent_business_analysis_match_expected.json`。

上述夹具均已通过对应 Schema 的结构验证。

## 当前边界

- Schema 合法不代表内容事实正确；
- 任务频率、自主程度、强度和出差等字段常常为 unknown；
- 个人经历仍需补充日期、行动、结果和可验证材料；
- 暂未绑定具体模型或 API 调用代码；
- 暂未建立数据库表。

## 下一步

首轮岗位画像 Prompt 回归已完成。下一步增加证据引用和重复条件校验，并测试个人画像 Prompt 与证据对齐 Prompt。
