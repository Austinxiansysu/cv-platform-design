# AI 结构化输出 Prompt 与评测设计 v1

更新日期：2026-09-21

状态：AI 产品设计第一版。严格 JSON Schema 已生成，暂不包含 API 调用代码和具体模型绑定。

## 一 这一步解决什么问题

系统已经定义个人画像、岗位画像和匹配逻辑，现在需要明确：

1. AI 每次接收什么输入；
2. AI 只能完成哪些判断；
3. AI 必须返回哪些固定字段；
4. 哪些分数由规则计算而不是 AI 猜测；
5. 如何发现幻觉、遗漏和错误推断；
6. 如何用 10 条 JD 验证输出质量。

## 二 总体架构

第一版不使用一个超长 Prompt 一次完成所有工作，而是拆成三个 AI 任务和一个规则层。

```text
简历 问卷 经历证据
        ↓
任务 A 个人画像提取
        ↓
结构化个人画像

原始 JD
        ↓
任务 B 岗位画像提取
        ↓
结构化岗位画像

个人画像 + 岗位画像 + 分析模式
        ↓
任务 C 证据对齐
        ↓
逐项匹配证据 缺口 未知 风险

结构化结果
        ↓
透明规则层
        ↓
分数 标签 双结论 用户页面
```

### 为什么拆开

- 个人事实只解析一次，避免不同 JD 下生成不同版本的用户经历；
- 岗位事实不受用户偏好影响；
- 证据对齐只比较两个已经确认的结构；
- 分数由固定权重计算，便于解释和测试；
- 任一模块出错时容易定位。

## 三 共同数据原则

### 1 证据对象

所有重要结论引用统一的证据对象：

| 字段 | 说明 |
|---|---|
| evidence_id | 当前输出内唯一编号 |
| source_type | resume、questionnaire、user_confirmed、jd、behavior |
| source_reference | 页码、段落、题号或原始字段 |
| source_text | 支持结论的最短必要原文 |
| claim_type | explicit、inferred、unknown |
| confidence | high、medium、low |

### 2 输入状态

每个 AI 任务必须先返回输入状态：

- sufficient：足以完成主要任务；
- partial：可以部分处理，但存在关键信息缺失；
- incompatible：输入不是预期材料；
- conflict：输入内部存在明显矛盾。

当输入不足时返回空值、未知项和补充问题，不能为了填满结构而编造内容。

### 3 未知值

结构化字段使用明确状态：

- known；
- unknown；
- not_applicable；
- conflicting。

空字符串不应同时表示未知、不适用和解析失败。

### 4 来源与判断分离

每个结构化对象尽量同时保存：

- 原始值；
- 标准化值；
- 判断依据；
- 是否需要用户确认。

## 四 任务 A 个人画像提取

### 1 输入

- 简历文本；
- 用户基本信息；
- 首次问卷；
- 经历证据表；
- 用户已经确认的画像字段。

### 2 AI 可以做

- 提取明确教育和经历事实；
- 识别技能与经历之间的证据关系；
- 将任务偏好映射到标准词表；
- 找出缺失或互相冲突的信息；
- 提出用户确认问题。

### 3 AI 不可以做

- 创造简历没有的成绩、技能、经历和结果；
- 根据学校推断能力水平；
- 根据一次浏览行为覆盖用户明确偏好；
- 把使用 AI 工具改写成 AI 产品经理经验；
- 把比赛项目改写成企业工作经验；
- 自行决定用户长期职业。

### 4 结构化输出契约

#### profile_meta

- profile_version；
- generated_at；
- input_status；
- source_ids；
- confirmation_status。

#### background

- school；
- college_or_major；
- degree；
- current_year；
- graduation_year；
- current_city；
- languages；
- optional_academic_records。

#### availability_constraints

- semester_internship_available；
- vacation_days_per_week_min；
- vacation_days_per_week_max；
- duration_months_min；
- duration_months_max；
- acceptable_locations；
- remote_preference；
- travel_preference；
- intensity_preference。

#### skills

每项包含：

- skill_name；
- normalized_skill；
- self_reported_level；
- evidence_ids；
- evidence_strength；
- last_used；
- displayable_artifact；
- confirmation_needed。

#### experiences

每项包含：

- experience_id；
- title；
- organization_or_context；
- start_date；
- end_date；
- problem；
- user_actions；
- tools；
- deliverables；
- outcomes；
- verifiable_materials；
- prohibited_claims；
- evidence_ids。

#### task_preferences

每项包含：

- task_name；
- preference_level；
- confidence；
- evidence_ids；
- status：confirmed、hypothesis、untested。

#### work_style_preferences

- exploration_vs_process；
- analysis_vs_execution；
- independent_vs_collaborative；
- visible_output_preference；
- technical_depth_preference；
- customer_facing_preference；
- repetition_tolerance；
- intensity_tolerance。

#### career_hypotheses

每项包含：

- direction_name；
- status：priority、exploring、deprioritized；
- supporting_evidence_ids；
- unresolved_questions；
- next_validation_action。

#### profile_gaps

- missing_information；
- evidence_gaps；
- confirmed_skill_gaps；
- contradictions；
- user_confirmation_questions。

#### evidence_registry

- 统一保存个人画像使用的原始证据；
- 其他字段只引用 evidence_id，避免重复复制长文本。

## 五 任务 B 岗位画像提取

### 1 输入

- 原始 JD 文本；
- 来源类型；
- 原始链接或截图引用；
- 采集日期。

不传入个人画像，避免岗位解析被用户偏好污染。

### 2 AI 可以做

- 提取岗位基本信息与资格条件；
- 区分必须、优先、背景说明和未知；
- 将职责拆成任务级字段；
- 识别工作对象与交付物；
- 识别官方职类与实际任务可能存在的偏差；
- 记录内部矛盾和未知信息。

### 3 AI 不可以做

- 根据公司名推断强度、文化或薪资；
- 把所有工具列表都判为必须；
- 从岗位名称补充未出现的任务；
- 把“深入参与”自动解释为高自主权；
- 推测录取概率；
- 判断某个具体用户是否适合。

### 4 结构化输出契约

#### job_meta

- job_id；
- original_title；
- company；
- team_or_department；
- source_type；
- source_reference；
- collected_at；
- posting_status；
- source_reliability；
- input_status。

#### basic_conditions

- locations；
- work_mode；
- recruitment_type；
- graduation_cohorts；
- degree_requirements；
- major_requirements；
- days_per_week；
- duration_months；
- earliest_start；
- language_requirements；
- other_hard_conditions。

每项条件包含：

- original_text；
- normalized_value；
- requirement_strength；
- evidence_id；
- status。

#### function_classification

- official_category；
- primary_function；
- secondary_functions；
- adjacent_role_names；
- title_task_consistency；
- consistency_explanation；
- confidence。

#### tasks

每项包含：

- task_id；
- normalized_task；
- original_text；
- importance；
- estimated_frequency；
- work_objects；
- deliverables；
- autonomy_level；
- claim_type；
- confidence；
- evidence_id。

频率和自主程度没有明确依据时必须为 unknown。

#### capability_requirements

每项包含：

- capability_name；
- capability_type；
- requirement_strength；
- expected_level；
- learnable_on_job；
- original_text；
- evidence_id；
- confidence。

#### tool_requirements

每项包含：

- tool_name；
- requirement_strength；
- expected_level；
- grouped_with_other_tools；
- original_text；
- evidence_id。

#### relevance_dimensions

- ai_relevance；
- data_relevance；
- finance_relevance；
- product_relevance；
- research_relevance；
- client_facing_relevance。

每个维度使用 0 到 3，并附 evidence_ids。

#### work_style

- customer_communication；
- cross_functional_collaboration；
- independent_analysis；
- research_vs_execution；
- repetitive_work；
- open_endedness；
- technical_depth；
- travel_or_client_site；
- intensity；
- evidence_ids。

#### job_uncertainties

- missing_fields；
- contradictions；
- sensitive_requirements；
- verification_questions；
- warnings。

#### evidence_registry

- 统一保存 JD 证据；
- 任务、条件和能力要求只引用 evidence_id。

## 六 任务 C 证据对齐

### 1 输入

- 已确认个人画像；
- 已确认岗位画像；
- analysis_mode：career_exploration、current_application、future_planning。

### 2 AI 可以做

- 将岗位任务与用户任务偏好对齐；
- 将岗位能力要求与用户经历证据对齐；
- 区分直接证据、可迁移证据和无证据；
- 识别偏好风险、证据缺口和信息缺口；
- 生成待确认问题；
- 提供简短可核验的解释。

### 3 AI 不可以做

- 直接决定总分；
- 修改个人或岗位事实；
- 因当前届别不符而降低职业方向匹配；
- 将无证据自动判为明确不会；
- 生成新的简历经历；
- 使用学校声誉推断胜任度。

### 4 结构化输出契约

#### match_meta

- match_id；
- profile_version；
- job_id；
- analysis_mode；
- input_status；
- warnings。

#### current_application_eligibility

- status：pass、pending、current_cycle_conflict、structural_conflict；
- passed_conditions；
- conflicting_conditions；
- unknown_conditions；
- time_snapshot_conditions；
- explanation。

#### task_alignments

每项包含：

- job_task_cluster_id；
- preference_alignment：positive、neutral、negative、untested；
- preference_evidence_ids；
- readiness_evidence_ids；
- readiness_evidence_level；
- preference_risk；
- explanation；
- confidence。

#### capability_alignments

每项包含：

- job_capability_id；
- status：supported、partially_supported、not_demonstrated、confirmed_gap、unknown；
- user_evidence_ids；
- gap_type；
- explanation；
- confidence。

#### career_direction_assessment

- supporting_points；
- opposing_points；
- exploration_questions；
- future_preparation_items。

#### gap_summary

- current_cycle_gaps；
- structural_feasibility_gaps；
- capability_gaps；
- evidence_gaps；
- preference_risks；
- information_gaps。

#### user_facing_explanation

- one_sentence_conclusion；
- highly_aligned_points；
- partially_aligned_points；
- main_risks；
- questions_before_application；
- resume_focus_candidates；
- prohibited_resume_additions。

#### profile_evidence_registry

- 保存本次对齐实际使用的用户证据子集；
- 不复制未参与判断的敏感信息。

## 七 透明规则层

规则层接收任务 C 的结构化结果，完成：

- 想做程度计算；
- 当前准备度计算；
- 职业探索价值计算；
- 职业方向摘要计算；
- 当前申请资格判断；
- 职业方向标签；
- 当前行动标签。

AI 不直接输出最终数值，避免不同调用对相同证据给出漂移分数。

规则层还负责检查：

- 是否存在没有证据的高分；
- 是否用其他优势抵消当前资格冲突；
- 是否把 unknown 当成 0；
- 是否遗漏反对理由；
- 是否出现未授权的简历新增事实。

## 八 Prompt 共同骨架

### 1 系统指令

```text
你是求职信息结构化分析器，不是职业决定者。

必须遵守：
1. 只使用输入材料中的事实，不补充不存在的经历、技能、成绩、职责或结果。
2. 所有重要结论必须提供对应证据。
3. 明确区分 explicit、inferred 和 unknown。
4. 明确区分 must、preferred、context 和 uncertain。
5. 输入没有说明的内容返回 unknown，不用常识猜测。
6. 不根据学校、公司、岗位名称或行业刻板印象推断能力、强度和文化。
7. 如果输入不足、冲突或不相关，使用输入状态和未知字段表达，不要为了填满结构而编造。
8. 只返回约定的结构化输出。
```

### 2 任务指令结构

每个任务 Prompt 包含：

- 当前任务；
- 输入材料边界；
- 字段定义；
- 允许的判断；
- 禁止的判断；
- 两到三个关键边界示例；
- 输出结构。

### 3 边界示例

#### 示例 A 简历没写 SQL

错误：用户不会 SQL。

正确：当前输入没有 SQL 使用证据，状态为 not_demonstrated 或 unknown，需用户确认。

#### 示例 B JD 写熟悉 SQL、Python、R 等工具

错误：SQL、Python 和 R 全部是硬性要求。

正确：如果原文没有说明全部必须，保留工具集合并将要求强度标为 uncertain。

#### 示例 C 岗位要求 2027 届 用户 2029 届

错误：岗位与用户匹配度低。

正确：current_application_eligibility 为 current_cycle_conflict；职业方向匹配继续正常分析。

#### 示例 D 用户用 AI 完成官网

错误：用户拥有 AI 产品经理经验。

正确：用户有 AI 工具应用和从需求到交付的项目证据，但没有正式 AI 产品经理、企业客户调研或产品指标证据。

## 九 个人画像 Prompt 草案

```text
任务：从用户提供的简历、问卷、经历证据和已确认字段中建立个人画像。

执行顺序：
1. 先判断输入状态；
2. 提取明确事实；
3. 建立技能与经历证据关联；
4. 提取任务和工作方式偏好；
5. 标记 AI 推断及其依据；
6. 识别未知、冲突和证据缺口；
7. 生成最少必要的用户确认问题。

禁止：
- 不得创造经历或结果；
- 不得把比赛改写成企业经验；
- 不得根据学校推断能力；
- 不得替用户确定永久职业标签。
```

## 十 岗位画像 Prompt 草案

```text
任务：把原始 JD 转换成不依赖具体用户的结构化岗位画像。

执行顺序：
1. 保存来源和原始标题；
2. 提取所有明确资格条件；
3. 区分必须、优先和背景说明；
4. 将职责拆成任务级字段；
5. 为任务识别工作对象和交付物；
6. 比较官方职类、岗位名称和实际任务；
7. 标记未知、冲突、敏感要求和核验问题。

禁止：
- 不得推断特定用户是否适合；
- 不得从公司名称推断强度；
- 不得把岗位亮点当成可验证成长结果；
- 不得把未说明的频率和自主程度写成事实。

数值条件规范：
- “至少 X–Y 天”不能直接得到“最多 Y 天”；保留可确认的最低值、将最高值设为未知，并加入核验问题；
- 只有 JD 明确给出更长时长为优先条件时才填写 preferred；若只写“实习 3 个月”，minimum=3、preferred=null；
- 页面摘要与任职要求出现不同数值时，分别保存最低要求与优先条件；只有两者无法同时成立时才标记为 conflict。
```

## 十一 证据对齐 Prompt 草案

```text
任务：根据已确认的个人画像和岗位画像进行逐项证据对齐。

执行顺序：
1. 读取 analysis_mode；
2. 独立判断当前申请资格；
3. 对每个核心任务判断偏好与准备证据；
4. 对每项能力要求查找直接或可迁移证据；
5. 分类当前批次、结构性、能力、证据、偏好和信息缺口；
6. 同时给出支持点和反对点；
7. 生成职业方向结论所需证据，但不计算最终分数。

禁止：
- 不得让当前届别冲突降低职业方向匹配；
- 不得把没有证据写成明确不会；
- 不得修改或补写任何经历；
- 不得直接生成最终分数和标签。

资格状态边界：
- 用户只在寒暑假实习，而 JD 最早开始时间或实习窗口未知时，状态为 pending，不得判 pass，也不得因当前正值学期而判 current_cycle_conflict；
- 只有 JD 明确的当期时间、届别、到岗或时长与用户当前条件不符时，才判 current_cycle_conflict；
- 一旦存在已确认的当期硬冲突，即使同时还有其他未知条件，状态仍为 current_cycle_conflict；未知信息不能把已确认冲突降级为 pending；
- 当前本科、未来是否读研尚未确定，而具体 JD 要求硕士在读时，当前岗位判 current_cycle_conflict；不得把“当前学历”同时写入 structural gap；
- structural_conflict 仅用于地点、出差、长期工作方式等已确认的稳定约束冲突；未知条件只能进入 pending/信息缺口。
```

## 十二 失败和异常处理

### 1 非 JD 输入

- input_status = incompatible；
- 不生成岗位任务；
- 返回输入类型说明和重新输入提示。

### 2 JD 信息不完整

- input_status = partial；
- 提取能够确认的部分；
- 缺失字段为 unknown；
- 生成补充问题。

### 3 多岗位混在一起

- input_status = conflict 或 partial；
- 不将不同岗位职责合并；
- 提示用户拆分输入。

### 4 简历和问卷矛盾

- 保留两项来源；
- 标记 conflict；
- 由用户确认，不由 AI 自动覆盖。

### 5 输出被截断或拒绝

- 前端不得把不完整结构当作有效结果；
- 保存错误类型；
- 允许重试但不能静默生成默认事实。

## 十三 首轮评测设计

### 1 测试对象

- 1 份个人画像；
- 10 条首批 JD；
- 3 条已有完整人工基准；
- 其余 7 条逐步补充人工标注。

所有 10 条默认采用 career_exploration 模式。当前招聘资格作为独立字段测试，不阻止岗位方向分析。

### 2 测试层级

#### 层级 A 结构正确

- 输出符合固定结构；
- 枚举值合法；
- 必填字段存在；
- unknown 使用一致；
- 没有额外未定义字段。

#### 层级 B 事实提取正确

- 公司、岗位、地点和届别正确；
- 出勤和时长正确；
- must 与 preferred 正确；
- 原文证据能支持结论。

#### 层级 C 语义理解正确

- 任务拆分合理；
- 岗位名称与实际任务差异识别正确；
- 工作对象和交付物合理；
- 未知信息没有被填成事实。

#### 层级 D 匹配解释正确

- 用户证据没有被夸大；
- 当前届别不影响职业方向判断；
- 缺口类型正确；
- 同时存在支持理由和反对理由；
- 简历适配候选不包含虚构内容。

### 3 严重程度

| 等级 | 定义 | 示例 |
|---|---|---|
| P0 | 会误导用户或制造虚假经历 | 编造技能、遗漏明确硬条件、把不存在经历写入简历 |
| P1 | 明显影响岗位理解或建议 | 把 FDE 误判为产品经理、把优先项判为必须 |
| P2 | 解释不够清楚但不改变主结论 | 任务命名不统一、次要未知项遗漏 |

### 4 第一版通过标准

- 编造用户经历：0 次；
- 编造 JD 要求：0 次；
- 明确硬条件遗漏：0 次；
- 当前届别错误影响方向分：0 次；
- must 与 preferred 准确率目标：至少 90%；
- 三条人工基准的方向标签全部一致；
- 三条人工基准的当前行动标签全部一致；
- 主要任务拆分与人工标注基本一致；
- 所有建议都有证据和反对理由。

这些数字是内部测试门槛，不代表产品已经经过大规模统计验证。

## 十四 错误案例表

每次测试记录：

| 字段 | 说明 |
|---|---|
| case_id | 错误编号 |
| jd_id | 岗位样本 |
| task_name | 个人画像、岗位画像或证据对齐 |
| expected | 人工标准 |
| actual | AI 输出 |
| severity | P0、P1、P2 |
| error_type | 编造、遗漏、误分类、过度推断、证据错误等 |
| likely_cause | Prompt、结构、输入或规则问题 |
| proposed_fix | 修改方案 |
| regression_case | 是否加入固定回归测试 |
| status | open、fixed、accepted |

## 十五 用户参与点

以下部分必须由用户参与，不能完全交给 AI：

1. 判断任务解释是否符合自己对岗位的理解；
2. 确认偏好和职业假设；
3. 确认经历证据是否被夸大；
4. 给 P0、P1、P2 错误定级；
5. 决定哪些输出信息真正帮助投递决策；
6. 审批 Prompt 中允许和禁止的推断边界。

## 十六 下一步

当前先完成概念结构，不实现 API。下一次行动：

以下工作已经完成：

- 飞书 FDE 和腾讯商业分析的完整期望输出；
- 字段冗余与缺失对照；
- 用户审批四项推断边界；
- 个人画像、岗位画像和证据对齐的严格 JSON Schema；
- 五组人工夹具结构验证。

下一步：使用三条人工基准进行第一次真实 Prompt 运行，记录 P0、P1 和 P2 错误；根据错误决定是否修改 Prompt 或 Schema，稳定后再生成后端类型。

## 十七 设计依据

本设计参考官方 OpenAI 文档中的原则：使用 JSON Schema 约束输出结构；使用清晰字段名称和描述；对用户输入不足或不兼容设置明确处理方式；通过评测验证结构设计和内容质量。结构化输出保证字段符合结构，但不能替代事实正确性和人工评测。
