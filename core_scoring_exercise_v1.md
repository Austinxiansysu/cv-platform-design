# 透明计分函数设计与实现说明 v1

状态：已实现并通过单元测试。实现位置：`src/matching/scoring.py`。

## 一 这一步解决什么问题

把已经确认的产品规则转换成第一个核心 Python 函数。这个函数不调用 AI，只读取结构化结果并透明地计算：

- 想做程度；
- 当前准备度；
- 职业探索价值；
- 偏好覆盖率；
- 是否允许显示总体方向摘要；
- 当前申请资格与职业方向的双结论。

## 二 为什么由用户参与

这段代码决定产品如何理解“匹配”。如果完全由 AI 编写，项目容易变成无法解释的黑箱。用户至少需要理解每个映射、权重和边界条件。

## 三 输入

函数接收已经验证的证据对齐结果和岗位任务簇：

```text
task_clusters
task_alignments
capability_alignments
career_direction_assessment
current_application_eligibility
```

## 四 映射规则

### 任务重要性

| 重要性 | 权重 |
|---|---:|
| core | 3 |
| important_support | 2 |
| general_support | 1 |

### 任务偏好

| 状态 | 分值 |
|---|---:|
| positive | 100 |
| neutral | 50 |
| negative | 0 |
| untested | 不进入分数，只降低覆盖率 |

### 任务准备证据

| 状态 | 分值 |
|---|---:|
| direct_strong | 100 |
| direct_basic | 75 |
| transferable | 50 |
| self_report_only | 25 |
| not_demonstrated | 0 |
| confirmed_gap | 0 |
| unknown | 不进入分数并降低置信度 |

### 能力准备证据

| 状态 | 分值 |
|---|---:|
| supported | 100 |
| partially_supported | 50 |
| not_demonstrated | 0 |
| confirmed_gap | 0 |
| unknown | 不进入分数并降低置信度 |

### 探索价值

| 等级 | 分值 |
|---|---:|
| high | 100 |
| medium | 70 |
| low | 30 |
| unknown | 不计算 |

探索价值计算：

```text
方向一致度 × 40% + 成长价值 × 60%
```

## 五 覆盖率门槛

想做程度的覆盖率为：

```text
已知偏好任务簇的权重总和 ÷ 全部任务簇权重总和
```

规则：

- 覆盖率不低于 50%：可以计算想做程度；
- 覆盖率低于 50%：想做程度返回 null；
- 想做程度为 null：总体方向摘要也返回 null；
- 页面显示已知匹配点和待验证任务，不伪造中性分。

## 六 准备度

第一版建议：

```text
任务准备证据 × 60% + 能力要求证据 × 40%
```

如果某一部分全部为 unknown，应降低结果置信度，而不是自动按 0 分处理。

## 七 总体方向摘要

只有在想做程度存在时才计算：

```text
想做程度 × 45%
+ 当前准备度 × 30%
+ 职业探索价值 × 25%
```

最终结果四舍五入到最接近的 5 分。

## 八 当前申请资格

当前申请资格不进入方向分数。

- pass：可以进入投递建议；
- pending：先补充信息；
- current_cycle_conflict：不投当前批次，保存岗位原型；
- structural_conflict：提示稳定现实冲突。

## 九 飞书 FDE 预期行为

四个任务簇权重：

- 客户调研与 AI 机会识别：core，偏好 untested；
- AI 与低代码方案搭建：core，偏好 positive；
- SOP 与模板：important_support，偏好 untested；
- 培训与持续支持：important_support，偏好 untested。

偏好覆盖率：

```text
3 ÷ (3 + 3 + 2 + 2) = 30%
```

因此：

- 想做程度：null；
- 总体方向摘要：null；
- 已知结论：方案搭建高度匹配；
- 待验证：客户调研、SOP、培训支持；
- 方向标签：值得探索；
- 当前行动：因 2027 届冲突，不投当前批次，保存岗位原型。

## 十 学习复核内容

阅读实现后，请用自己的语言写 8 到 15 行伪代码，描述：

1. 如何统计全部任务权重；
2. 如何统计已知偏好任务权重；
3. 如何计算覆盖率；
4. 覆盖不足时返回什么；
5. 覆盖足够时如何加权；
6. 为什么 eligibility 不进入方向分数。

对应单元测试位于 `tests/test_scoring.py`，覆盖偏好覆盖率、未知处理、届别解耦和真实飞书输出。
