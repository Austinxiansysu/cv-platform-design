import json
from pathlib import Path


ROOT = Path("/Users/xianjianhua/Desktop/CV platform design")
SCHEMAS = ROOT / "schemas"
FIXTURES = ROOT / "fixtures"
SCHEMAS.mkdir(exist_ok=True)


def obj(properties, description=None):
    value = {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(properties.keys()),
    }
    if description:
        value["description"] = description
    return value


def arr(items, description=None):
    value = {"type": "array", "items": items}
    if description:
        value["description"] = description
    return value


def string(description=None, enum=None):
    value = {"type": "string"}
    if description:
        value["description"] = description
    if enum:
        value["enum"] = enum
    return value


def integer(description=None, minimum=None, maximum=None):
    value = {"type": "integer"}
    if description:
        value["description"] = description
    if minimum is not None:
        value["minimum"] = minimum
    if maximum is not None:
        value["maximum"] = maximum
    return value


def boolean(description=None):
    value = {"type": "boolean"}
    if description:
        value["description"] = description
    return value


def nullable(base):
    return {"anyOf": [base, {"type": "null"}]}


def ref(name):
    return {"$ref": f"#/$defs/{name}"}


EVIDENCE = obj({
    "evidence_id": string("当前输出内唯一证据编号"),
    "source_type": string(enum=["resume", "questionnaire", "user_confirmed", "jd", "behavior"]),
    "source_reference": string("页码、段落、题号或原始字段"),
    "source_text": string("支持结论的最短必要原文"),
    "claim_type": string(enum=["explicit", "inferred", "unknown"]),
    "confidence": string(enum=["high", "medium", "low"]),
})


STATUS = string(enum=["known", "unknown", "not_applicable", "conflicting"])
CONFIDENCE = string(enum=["high", "medium", "low"])
REQ_STRENGTH = string(enum=["must", "preferred", "role_context", "background", "uncertain"])


def wrap(name, schema, description):
    return {
        "type": "json_schema",
        "name": name,
        "strict": True,
        "description": description,
        "schema": schema,
    }


graduation_condition = obj({
    "status": STATUS,
    "values": arr(string()),
    "requirement_strength": REQ_STRENGTH,
    "evidence_id": nullable(string()),
})

degree_condition = obj({
    "status": STATUS,
    "minimum_degree": nullable(string()),
    "requirement_strength": REQ_STRENGTH,
    "evidence_id": nullable(string()),
})

major_condition = obj({
    "status": STATUS,
    "must_have": arr(string()),
    "preferred": arr(string()),
    "evidence_id": nullable(string()),
})

days_condition = obj({
    "status": STATUS,
    "minimum": nullable(integer(minimum=0, maximum=7)),
    "maximum": nullable(integer(minimum=0, maximum=7)),
    "evidence_id": nullable(string()),
})

duration_condition = obj({
    "status": STATUS,
    "minimum": nullable(integer(minimum=0)),
    "preferred": nullable(integer(minimum=0)),
    "evidence_id": nullable(string()),
})

date_condition = obj({
    "status": STATUS,
    "value": nullable(string()),
    "evidence_id": nullable(string()),
})

language_requirement = obj({
    "language": string(),
    "expected_level": string(),
    "requirement_strength": REQ_STRENGTH,
    "evidence_id": string(),
})

other_condition = obj({
    "condition_name": string(),
    "normalized_value": string(),
    "requirement_strength": REQ_STRENGTH,
    "gate_type": string(enum=["hard_gate", "qualitative_requirement", "context"]),
    "evidence_id": string(),
})

task = obj({
    "task_id": string(),
    "normalized_task": string(),
    "original_text": string(),
    "importance": string(enum=["core", "important_support", "general_support"]),
    "estimated_frequency": string(enum=["high", "medium", "low", "unknown"]),
    "work_objects": arr(string()),
    "deliverables": arr(string()),
    "autonomy_level": string(enum=["explicit_independent", "explicit_assist", "mixed", "unknown"]),
    "claim_type": string(enum=["explicit", "inferred", "unknown"]),
    "confidence": CONFIDENCE,
    "evidence_ids": arr(string()),
})

task_cluster = obj({
    "cluster_id": string(),
    "cluster_name": string(),
    "task_ids": arr(string()),
    "importance": string(enum=["core", "important_support", "general_support"]),
    "rationale": string(),
    "evidence_ids": arr(string()),
})

capability = obj({
    "capability_id": string(),
    "capability_name": string(),
    "capability_type": string(enum=["technical", "business_analysis", "research", "product", "communication", "motivation", "general"]),
    "requirement_strength": REQ_STRENGTH,
    "claim_type": string(enum=["explicit", "inferred", "unknown"]),
    "expected_level": string(),
    "learnable_on_job": string(enum=["yes", "partly", "no", "unknown"]),
    "original_text": string(),
    "evidence_id": string(),
    "confidence": CONFIDENCE,
})

experience_requirement = obj({
    "experience_name": string(),
    "requirement_strength": REQ_STRENGTH,
    "claim_type": string(enum=["explicit", "inferred", "unknown"]),
    "original_text": string(),
    "evidence_id": string(),
})

tool_requirement = obj({
    "tool_name": string(),
    "requirement_strength": REQ_STRENGTH,
    "expected_level": string(),
    "grouped_with_other_tools": boolean(),
    "original_text": string(),
    "evidence_id": string(),
})

relevance = obj({
    "level": integer(minimum=0, maximum=3),
    "evidence_ids": arr(string()),
})

work_style_signal = obj({
    "status": string(enum=["known", "possible", "unknown", "conflicting"]),
    "value": nullable(string()),
    "claim_type": string(enum=["explicit", "inferred", "unknown"]),
    "evidence_ids": arr(string()),
})

JOB_SCHEMA = obj({
    "job_meta": obj({
        "job_id": string(),
        "original_title": string(),
        "company": nullable(string()),
        "team_or_department": nullable(string()),
        "source_type": string(enum=["company_official", "school_channel", "recruiting_platform", "referral_repost", "unknown"]),
        "source_reference": string(),
        "collected_at": string(),
        "posting_status": string(enum=["available_when_collected", "offline", "unknown"]),
        "source_reliability": CONFIDENCE,
        "input_status": string(enum=["sufficient", "partial", "incompatible", "conflict"]),
    }),
    "basic_conditions": obj({
        "locations": arr(string()),
        "work_mode": string(enum=["onsite", "remote", "hybrid", "onsite_or_unknown", "unknown"]),
        "interview_mode": nullable(string()),
        "recruitment_type": string(),
        "graduation_cohorts": graduation_condition,
        "degree_requirements": degree_condition,
        "major_requirements": major_condition,
        "days_per_week": days_condition,
        "duration_months": duration_condition,
        "earliest_start": date_condition,
        "language_requirements": arr(language_requirement),
        "other_application_conditions": arr(other_condition),
    }),
    "function_classification": obj({
        "official_category": nullable(string()),
        "primary_function": string(),
        "secondary_functions": arr(string()),
        "adjacent_role_names": arr(string()),
        "title_task_consistency": string(enum=["high", "medium", "low", "unknown"]),
        "consistency_explanation": string(),
        "title_transparency": string(enum=["high", "medium", "low", "unknown"]),
        "transparency_explanation": string(),
        "confidence": CONFIDENCE,
        "evidence_ids": arr(string()),
    }),
    "tasks": arr(task),
    "task_clusters": arr(task_cluster, "用于偏好匹配和计分的去重任务簇"),
    "capability_requirements": arr(capability),
    "experience_requirements": arr(experience_requirement),
    "tool_requirements": arr(tool_requirement),
    "relevance_dimensions": obj({
        "ai_relevance": relevance,
        "data_relevance": relevance,
        "finance_relevance": relevance,
        "product_relevance": relevance,
        "research_relevance": relevance,
        "client_facing_relevance": relevance,
    }),
    "work_style": obj({
        "customer_communication": work_style_signal,
        "cross_functional_collaboration": work_style_signal,
        "independent_analysis": work_style_signal,
        "research_vs_execution": work_style_signal,
        "repetitive_work": work_style_signal,
        "open_endedness": work_style_signal,
        "technical_depth": work_style_signal,
        "travel_or_client_site": work_style_signal,
        "intensity": work_style_signal,
    }),
    "job_uncertainties": obj({
        "missing_fields": arr(string()),
        "contradictions": arr(string()),
        "sensitive_requirements": arr(string()),
        "verification_questions": arr(string()),
        "warnings": arr(string()),
    }),
    "evidence_registry": arr(EVIDENCE),
}, "不依赖具体用户的结构化岗位画像")


task_alignment = obj({
    "job_task_cluster_id": string(),
    "preference_alignment": string(enum=["positive", "neutral", "negative", "untested"]),
    "preference_evidence_ids": arr(string()),
    "readiness_evidence_ids": arr(string()),
    "readiness_evidence_level": string(enum=["direct_strong", "direct_basic", "transferable", "self_report_only", "not_demonstrated", "confirmed_gap", "unknown"]),
    "preference_risk": nullable(string()),
    "explanation": string(),
    "confidence": CONFIDENCE,
})

capability_alignment = obj({
    "job_capability_id": string(),
    "status": string(enum=["supported", "partially_supported", "not_demonstrated", "confirmed_gap", "unknown"]),
    "user_evidence_ids": arr(string()),
    "gap_type": string(enum=["none", "current_cycle_gap", "structural_gap", "capability_gap", "evidence_gap", "preference_risk", "information_gap"]),
    "explanation": string(),
    "confidence": CONFIDENCE,
})

MATCH_SCHEMA = obj({
    "match_meta": obj({
        "match_id": string(),
        "profile_version": string(),
        "job_id": string(),
        "analysis_mode": string(enum=["career_exploration", "current_application", "future_planning"]),
        "input_status": string(enum=["sufficient", "partial", "incompatible", "conflict"]),
        "warnings": arr(string()),
    }),
    "current_application_eligibility": obj({
        "status": string(enum=["pass", "pending", "current_cycle_conflict", "structural_conflict"]),
        "passed_conditions": arr(string()),
        "conflicting_conditions": arr(string()),
        "unknown_conditions": arr(string()),
        "time_snapshot_conditions": arr(string()),
        "explanation": string(),
    }),
    "task_alignments": arr(task_alignment),
    "capability_alignments": arr(capability_alignment),
    "career_direction_assessment": obj({
        "direction_alignment": string(enum=["high", "medium", "low", "unknown"]),
        "growth_value": string(enum=["high", "medium", "low", "unknown"]),
        "confidence": CONFIDENCE,
        "supporting_points": arr(string()),
        "opposing_points": arr(string()),
        "exploration_questions": arr(string()),
        "future_preparation_items": arr(string()),
    }),
    "gap_summary": obj({
        "current_cycle_gaps": arr(string()),
        "structural_feasibility_gaps": arr(string()),
        "capability_gaps": arr(string()),
        "evidence_gaps": arr(string()),
        "preference_risks": arr(string()),
        "information_gaps": arr(string()),
    }),
    "user_facing_explanation": obj({
        "one_sentence_conclusion": string(),
        "highly_aligned_points": arr(string()),
        "partially_aligned_points": arr(string()),
        "main_risks": arr(string()),
        "questions_before_application": arr(string()),
        "resume_focus_candidates": arr(string()),
        "prohibited_resume_additions": arr(string()),
    }),
    "profile_evidence_registry": arr(EVIDENCE),
}, "个人画像与岗位画像之间的逐项证据对齐，不包含最终分数")


profile_skill = obj({
    "skill_id": string(),
    "skill_name": string(),
    "normalized_skill": string(),
    "self_reported_level": string(),
    "evidence_ids": arr(string()),
    "evidence_strength": string(enum=["direct_strong", "direct_basic", "transferable", "self_report_only", "not_demonstrated", "confirmed_gap", "unknown"]),
    "last_used": nullable(string()),
    "displayable_artifact": nullable(string()),
    "confirmation_needed": boolean(),
})

experience = obj({
    "experience_id": string(),
    "title": string(),
    "organization_or_context": nullable(string()),
    "start_date": nullable(string()),
    "end_date": nullable(string()),
    "problem": nullable(string()),
    "user_actions": arr(string()),
    "tools": arr(string()),
    "deliverables": arr(string()),
    "outcomes": arr(string()),
    "verifiable_materials": arr(string()),
    "prohibited_claims": arr(string()),
    "evidence_ids": arr(string()),
    "confirmation_needed": boolean(),
})

task_preference = obj({
    "task_name": string(),
    "preference_level": string(enum=["strong_dislike", "dislike", "untested", "like", "strong_like"]),
    "confidence": CONFIDENCE,
    "evidence_ids": arr(string()),
    "status": string(enum=["confirmed", "hypothesis", "untested"]),
})

work_preference = obj({
    "dimension_name": string(),
    "value": string(),
    "confidence": CONFIDENCE,
    "evidence_ids": arr(string()),
    "status": string(enum=["confirmed", "hypothesis", "untested"]),
})

career_hypothesis = obj({
    "direction_name": string(),
    "status": string(enum=["priority", "exploring", "deprioritized"]),
    "supporting_evidence_ids": arr(string()),
    "unresolved_questions": arr(string()),
    "next_validation_action": string(),
})

PROFILE_SCHEMA = obj({
    "profile_meta": obj({
        "profile_version": string(),
        "generated_at": string(),
        "input_status": string(enum=["sufficient", "partial", "incompatible", "conflict"]),
        "source_ids": arr(string()),
        "confirmation_status": string(enum=["confirmed", "partially_confirmed", "unconfirmed"]),
    }),
    "background": obj({
        "school": nullable(string()),
        "college_or_major": nullable(string()),
        "degree": nullable(string()),
        "current_year": nullable(string()),
        "graduation_year": nullable(integer()),
        "current_city": nullable(string()),
        "languages": arr(string()),
        "optional_academic_records": arr(string()),
    }),
    "availability_constraints": obj({
        "semester_internship_available": boolean(),
        "vacation_days_per_week_min": nullable(integer(minimum=0, maximum=7)),
        "vacation_days_per_week_max": nullable(integer(minimum=0, maximum=7)),
        "duration_months_min": nullable(integer(minimum=0)),
        "duration_months_max": nullable(integer(minimum=0)),
        "acceptable_locations": arr(string()),
        "remote_preference": string(enum=["accept", "conditional", "reject", "unknown"]),
        "travel_preference": string(enum=["accept", "conditional", "prefer_not", "reject", "unknown"]),
        "intensity_preference": string(enum=["low", "medium", "high", "unknown"]),
    }),
    "skills": arr(profile_skill),
    "experiences": arr(experience),
    "task_preferences": arr(task_preference),
    "work_style_preferences": arr(work_preference),
    "career_hypotheses": arr(career_hypothesis),
    "profile_gaps": obj({
        "missing_information": arr(string()),
        "evidence_gaps": arr(string()),
        "confirmed_skill_gaps": arr(string()),
        "contradictions": arr(string()),
        "user_confirmation_questions": arr(string()),
    }),
    "evidence_registry": arr(EVIDENCE),
}, "仅由简历、问卷和用户确认材料建立的结构化个人画像")


profile_fixture = {
    "profile_meta": {
        "profile_version": "profile-v1",
        "generated_at": "2026-09-21",
        "input_status": "partial",
        "source_ids": ["conversation-profile", "jd-analysis-workbook"],
        "confirmation_status": "partially_confirmed",
    },
    "background": {
        "school": "中山大学",
        "college_or_major": "岭南学院金融系",
        "degree": "本科",
        "current_year": "大二",
        "graduation_year": 2029,
        "current_city": "广州",
        "languages": [],
        "optional_academic_records": [],
    },
    "availability_constraints": {
        "semester_internship_available": False,
        "vacation_days_per_week_min": 4,
        "vacation_days_per_week_max": 5,
        "duration_months_min": 2,
        "duration_months_max": 3,
        "acceptable_locations": ["广州", "深圳", "远程"],
        "remote_preference": "accept",
        "travel_preference": "prefer_not",
        "intensity_preference": "low",
    },
    "skills": [
        {"skill_id": "P-S01", "skill_name": "Python", "normalized_skill": "python", "self_reported_level": "基础", "evidence_ids": ["P-E04"], "evidence_strength": "self_report_only", "last_used": None, "displayable_artifact": None, "confirmation_needed": True},
        {"skill_id": "P-S02", "skill_name": "AI工具应用", "normalized_skill": "ai_tool_usage", "self_reported_level": "有项目实践", "evidence_ids": ["P-E01"], "evidence_strength": "direct_basic", "last_used": None, "displayable_artifact": "企业官网项目", "confirmation_needed": False},
        {"skill_id": "P-S03", "skill_name": "结构化与定量分析", "normalized_skill": "structured_quantitative_analysis", "self_reported_level": "有比赛实践", "evidence_ids": ["P-E02", "P-E03"], "evidence_strength": "transferable", "last_used": None, "displayable_artifact": None, "confirmation_needed": False}
    ],
    "experiences": [
        {"experience_id": "P-X01", "title": "企业官网项目", "organization_or_context": "企业项目", "start_date": None, "end_date": None, "problem": "企业官网需求", "user_actions": ["使用AI工具参与需求到交付"], "tools": ["AI工具"], "deliverables": ["企业官网"], "outcomes": [], "verifiable_materials": [], "prohibited_claims": ["AI产品经理经验", "企业级FDE经验"], "evidence_ids": ["P-E01"], "confirmation_needed": True},
        {"experience_id": "P-X02", "title": "岭南杯案例分析大赛", "organization_or_context": "比赛", "start_date": None, "end_date": None, "problem": None, "user_actions": [], "tools": [], "deliverables": [], "outcomes": [], "verifiable_materials": [], "prohibited_claims": ["企业商业分析经验"], "evidence_ids": ["P-E02"], "confirmation_needed": True},
        {"experience_id": "P-X03", "title": "数学建模比赛", "organization_or_context": "比赛", "start_date": None, "end_date": None, "problem": None, "user_actions": [], "tools": ["Python"], "deliverables": [], "outcomes": [], "verifiable_materials": [], "prohibited_claims": ["企业数据分析经验"], "evidence_ids": ["P-E03"], "confirmation_needed": True}
    ],
    "task_preferences": [
        {"task_name": "AI工具应用", "preference_level": "strong_like", "confidence": "high", "evidence_ids": ["P-E01"], "status": "confirmed"},
        {"task_name": "快速搭建解决方案", "preference_level": "strong_like", "confidence": "medium", "evidence_ids": ["P-E01"], "status": "hypothesis"},
        {"task_name": "商业与行业分析", "preference_level": "like", "confidence": "medium", "evidence_ids": ["P-E02"], "status": "hypothesis"},
        {"task_name": "材料与档案整理", "preference_level": "dislike", "confidence": "medium", "evidence_ids": ["P-E05"], "status": "confirmed"},
        {"task_name": "企业客户沟通", "preference_level": "untested", "confidence": "low", "evidence_ids": [], "status": "untested"}
    ],
    "work_style_preferences": [
        {"dimension_name": "analysis_vs_execution", "value": "偏好分析与解决问题", "confidence": "high", "evidence_ids": ["P-E01", "P-E02"], "status": "confirmed"},
        {"dimension_name": "visible_output", "value": "偏好可见交付成果", "confidence": "high", "evidence_ids": ["P-E01"], "status": "confirmed"},
        {"dimension_name": "technical_depth", "value": "理解技术并动手但不以纯编程为核心", "confidence": "medium", "evidence_ids": ["P-E01"], "status": "hypothesis"},
        {"dimension_name": "customer_facing", "value": "未验证", "confidence": "low", "evidence_ids": [], "status": "untested"}
    ],
    "career_hypotheses": [
        {"direction_name": "AI解决方案或FDE", "status": "priority", "supporting_evidence_ids": ["P-E01"], "unresolved_questions": ["是否喜欢客户沟通与销售支持"], "next_validation_action": "分析并体验相似岗位任务"},
        {"direction_name": "商业或战略分析", "status": "priority", "supporting_evidence_ids": ["P-E02", "P-E03"], "unresolved_questions": ["是否喜欢长期行业研究与跨团队推进"], "next_validation_action": "完成真实公司分析样本"},
        {"direction_name": "投后管理", "status": "deprioritized", "supporting_evidence_ids": ["P-E05"], "unresolved_questions": ["是否喜欢经营分析和风险控制部分"], "next_validation_action": "暂不优先申请"}
    ],
    "profile_gaps": {
        "missing_information": ["英语能力证据", "项目日期与量化结果"],
        "evidence_gaps": ["企业客户调研", "SQL", "用户研究", "跨团队项目推进"],
        "confirmed_skill_gaps": [],
        "contradictions": [],
        "user_confirmation_questions": ["补充三段经历的行动、结果和可验证材料"]
    },
    "evidence_registry": [
        {"evidence_id": "P-E01", "source_type": "user_confirmed", "source_reference": "企业官网项目", "source_text": "使用AI完成企业官网需求到交付", "claim_type": "explicit", "confidence": "medium"},
        {"evidence_id": "P-E02", "source_type": "user_confirmed", "source_reference": "岭南杯", "source_text": "案例分析比赛经历", "claim_type": "explicit", "confidence": "medium"},
        {"evidence_id": "P-E03", "source_type": "user_confirmed", "source_reference": "数学建模比赛", "source_text": "定量分析和建模经历", "claim_type": "explicit", "confidence": "medium"},
        {"evidence_id": "P-E04", "source_type": "questionnaire", "source_reference": "用户背景", "source_text": "学过Python、Pandas、NumPy和Matplotlib基础", "claim_type": "explicit", "confidence": "high"},
        {"evidence_id": "P-E05", "source_type": "user_confirmed", "source_reference": "投后管理JD分析", "source_text": "不偏好长期材料、档案和合规整理", "claim_type": "explicit", "confidence": "medium"}
    ]
}


outputs = {
    SCHEMAS / "profile.schema.json": wrap("candidate_profile_v1", PROFILE_SCHEMA, "个人画像结构化输出"),
    SCHEMAS / "job_profile.schema.json": wrap("job_profile_v1", JOB_SCHEMA, "岗位画像结构化输出"),
    SCHEMAS / "match_alignment.schema.json": wrap("match_alignment_v1", MATCH_SCHEMA, "个人与岗位的证据对齐输出"),
    SCHEMAS / "profile.output.schema.json": PROFILE_SCHEMA,
    SCHEMAS / "job_profile.output.schema.json": JOB_SCHEMA,
    SCHEMAS / "match_alignment.output.schema.json": MATCH_SCHEMA,
    FIXTURES / "profile_expected.json": profile_fixture,
}

for path, value in outputs.items():
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path)
