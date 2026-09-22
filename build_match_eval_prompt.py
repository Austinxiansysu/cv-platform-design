import argparse
import json
from pathlib import Path


INSTRUCTIONS = """你是求职证据对齐分析器，不是职业决定者。

任务：根据已确认的个人画像和岗位画像，生成逐项证据对齐结果。

规则：
1. analysis_mode 固定为 career_exploration。
2. 当前招聘届别冲突只进入 current_application_eligibility，不得降低职业方向判断。
3. task_alignments 必须逐项引用 job_profile.task_clusters 的 cluster_id，不能引用原始 task_id。
4. 用户没有证据时使用 not_demonstrated，不得写成 confirmed_gap；只有用户明确确认不会时才能使用 confirmed_gap。
5. 比赛经历通常是 transferable，不得改写为企业工作经验。
6. 使用 AI 完成官网不能改写为 AI 产品经理、企业客户调研或 FDE 经验。
7. 同时给出支持点和反对点。
8. 不计算最终分数和标签。
9. resume_focus_candidates 只能引用真实经历；prohibited_resume_additions 明确禁止添加不存在的内容。
10. 所有证据引用必须来自个人画像 evidence_registry；岗位事实使用岗位对象中的证据，不复制进 profile_evidence_registry。
11. match_id 固定为 MATCH-P001-JD007，profile_version 固定为 profile-v1，job_id 固定为 JD-007。
12. current_application_eligibility 只判断学历、届别、地点、时间等申请条件；技能和兴趣不能写进 passed_conditions。
13. status=not_demonstrated 时 gap_type 必须为 evidence_gap；只有用户明确确认缺少能力时才使用 capability_gap。
14. 未知的时间、出差、强度或工作方式进入 information_gaps，不能写成已经确认的 structural_feasibility_gaps。
15. 不得把对一种材料工作的负向偏好推广到所有文档任务；用户不喜欢档案、台账和合规整理，不等于已经确认不喜欢SOP和演示模板。没有直接偏好证据时使用 untested，并单独提示风险。
16. capability_gaps 只保存用户明确确认缺少的能力；未体验和未证明进入 evidence_gaps。
17. career_direction_assessment 必须给出 direction_alignment、growth_value 和 confidence。方向一致度依据用户已确认的职业假设；成长价值依据可学习任务和证据缺口，不得依据招聘宣传。
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--job", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    content = INSTRUCTIONS + "\n个人画像：\n" + json.dumps(profile, ensure_ascii=False, indent=2)
    content += "\n\n岗位画像：\n" + json.dumps(job, ensure_ascii=False, indent=2) + "\n"
    Path(args.output).write_text(content, encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
