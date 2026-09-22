# 结构化输出 Schema 验证报告 v1

更新日期：2026-09-21

## 一 验证对象

| Schema | 对应夹具 |
|---|---|
| profile.schema.json | profile_expected.json |
| job_profile.schema.json | fde_job_profile_expected.json |
| job_profile.schema.json | tencent_business_analysis_job_profile_expected.json |
| match_alignment.schema.json | fde_match_expected.json |
| match_alignment.schema.json | tencent_business_analysis_match_expected.json |

## 二 验证结果

五组 Schema 与夹具组合全部通过。

## 三 严格模式结构检查

三份 Schema 均通过以下检查：

- 根节点为 object；
- 每个 object 都设置 `additionalProperties: false`；
- 每个 object 的 properties 与 required 完全一致；
- 未知或可选值通过 `null`、空数组或状态枚举表达；
- 没有使用动态额外字段；
- JSON 文件语法有效。

## 四 经过样本修正的字段

### 工作方式

原先使用模糊字符串，现在拆为：

- status；
- value；
- claim_type；
- evidence_ids。

这样可以区分“明确高频客户沟通”“可能需要客户沟通”和“完全未知”。

### 自主程度

统一为：

- explicit_independent；
- explicit_assist；
- mixed；
- unknown。

不再把“可能独立”混入枚举值。

### 工具要求

增加 `role_context`，用于表达岗位工作中会使用某工具，但 JD 没要求候选人入职前已经熟练。

### 时间条件

证据对齐中单独保存：

- current_cycle_conflict；
- structural_conflict；
- time_snapshot_conditions。

## 五 尚未验证的内容

本轮只验证结构，不代表以下内容已经正确：

- AI 是否能从原始文本稳定生成这些字段；
- 任务拆分是否与人工标准一致；
- 必须和优先是否会被误判；
- 证据引用是否准确；
- 不同模型的输出是否一致；
- 实际调用成本与速度。

这些问题需要下一步 Prompt 回归测试解决。
