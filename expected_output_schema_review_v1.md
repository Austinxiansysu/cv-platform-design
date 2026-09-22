# 飞书 FDE 与腾讯商业分析结构化输出对照 v1

更新日期：2026-09-21

## 一 已生成的测试夹具

- `fixtures/fde_job_profile_expected.json`
- `fixtures/fde_match_expected.json`
- `fixtures/tencent_business_analysis_job_profile_expected.json`
- `fixtures/tencent_business_analysis_match_expected.json`

这些文件是人工期望输出，不是模型生成结果。后续 AI 输出应与它们比较。

## 二 两条岗位共同需要的字段

两个案例都证明以下字段必要：

- 原始标题、公司、团队与来源；
- 当前招聘条件及未知状态；
- 官方职类、主职能和次职能；
- 任务级拆分；
- 工作对象、交付物和自主程度；
- 能力要求与要求强度；
- 相关度维度；
- 工作方式；
- 未知信息与核验问题；
- 证据注册表；
- 当前申请资格和职业方向分离；
- 任务偏好与准备证据分离；
- 支持理由和反对理由同时存在。

## 三 只有飞书案例显著触发的字段

- 客户现场和出差可能性；
- 销售支持属性；
- AI 方案搭建；
- 无代码或低代码工具；
- SOP、模板、培训和技术支持；
- 岗位名称对普通用户不透明；
- 当前招聘届别明确冲突但职业方向高匹配。

这些字段不能因为腾讯案例不需要就删除，否则系统无法识别 FDE 这类新型交叉岗位。

## 四 只有腾讯案例显著触发的字段

- 多个事业群但具体团队未知；
- 定性与定量研究并存；
- 战略分析与商业计划；
- 跨团队和跨事业群项目；
- 英语要求；
- 当前岗位信息不完整但任务画像可分析。

这证明岗位来源可靠不等于信息完整，`source_reliability` 和 `input_status` 必须分开。

## 五 发现的 Schema 缺口

### 1 缺少统一证据注册表

原设计分散提到 evidence_id，但没有把 `evidence_registry` 明确列入每个任务的顶层输出。现在应正式加入：

- 岗位画像输出包含 `evidence_registry`；
- 证据对齐输出包含 `profile_evidence_registry`；
- 每个结论只保存 evidence_id，不重复复制长文本。

### 2 当前资格状态需要区分时间快照

仅有 conflict 不够。新增：

- `current_cycle_conflict`：届别、发布时间、当期到岗日期不符；
- `structural_conflict`：地点、出差、长期工作方式等稳定冲突；
- `time_snapshot_conditions`：记录只对当前招聘批次有效的条件。

### 3 工具要求需要 role_context

飞书岗位职责要求使用飞书工具，但任职要求没有明确要求入职前已经熟练。因此新增 `role_context`，避免把工作中会使用的工具全部判为应聘硬门槛。

### 4 工作方式字段不能强制给确定答案

客户沟通、研究执行比例、技术深度等经常只能部分判断。字段必须允许：

- known；
- possible；
- unknown；
- conflicting。

不能通过模糊字符串无限扩展。真正 JSON Schema 应将状态和值拆开。

### 5 自主程度需要更严格的枚举

当前样本出现：

- assist；
- partly_independent_or_unknown；
- unknown。

正式 Schema 应改成：

- explicit_independent；
- explicit_assist；
- mixed；
- unknown。

不能把推断混进枚举值。

### 6 需要保留岗位级警告

例如：

- FDE 不能直接等同于 AI 产品经理；
- 腾讯不同事业群可能不是完全相同的岗位内容。

警告应来自岗位证据，而不是一般职业常识。

## 六 建议删除或延后显示的字段

### estimated_frequency

多数 JD 不提供任务频率。字段可以保留在机器结构中，但默认不展示；只有明确证据时才显示。

### autonomy_level

字段重要，但当前经常未知。保留用于面试问题生成，不作为第一版评分项。

### learnable_on_job

多数 JD 不会明确说明。除非有培训、导师或零经验表述，否则应为 unknown，不进入第一版评分。

## 七 字段命名调整

| 原字段 | 调整后 | 原因 |
|---|---|---|
| 现实可行性 | current_application_eligibility | 避免影响职业方向判断 |
| 总体匹配度 | career_direction_summary | 明确它不是录取概率 |
| 硬性缺口 | current_cycle_gap 或 structural_gap | 区分时间快照和稳定冲突 |
| 相关经验 | evidence_level | 避免把经历名称直接当能力 |
| 工作强度 | intensity.status + intensity.value | 区分未知和明确高强度 |

## 八 人工基准的暂定规则输出

### 飞书 FDE

- 职业方向摘要：75；
- 职业方向标签：优先方向或值得探索；
- 当前申请资格：current_cycle_conflict；
- 当前行动：不投当前批次，保存岗位原型；
- 主要证据：AI 官网项目；
- 主要风险：客户沟通、销售支持、SOP 与培训偏好未知。

### 腾讯商业分析

- 职业方向摘要：75；
- 职业方向标签：优先方向或值得探索；
- 当前申请资格：pending；
- 当前行动：当前不作为投递对象，保留岗位原型；
- 主要证据：岭南杯和数学建模；
- 主要风险：用户研究、跨团队推进和真实业务经验不足。

## 九 是否可以冻结

字段结构已经能够覆盖两种差异较大的岗位，但在转换成正式 JSON Schema 前需要用户确认四个产品判断：

1. FDE 的培训和技术支持是否应作为独立任务展示；
2. 腾讯商业分析是否应把跨团队推进与分析任务分开；
3. 当前没有证据的能力应显示为“未证明”而不是“不会”；
4. 当前招聘届别不应降低职业方向分。

如果四项均认可，则下一步可冻结字段并生成真正的 JSON Schema。
