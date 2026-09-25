"""Auditable, mechanical corrections for recurring JD extraction mistakes."""

from __future__ import annotations

import re
from typing import Any


def _compact(value: Any) -> str:
    return "".join(str(value or "").lower().split()).replace("；", "").replace("，", "")


def normalize_pre_schema(value: Any) -> list[str]:
    """Map one known model-only enum error before structural validation."""
    changes: list[str] = []

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            if item.get("requirement_strength") == "unknown":
                item["requirement_strength"] = "uncertain"
                changes.append("未知要求强度改为 Schema 允许的不确定")
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return changes


def _evidence_from_duties(evidence_item: dict[str, Any] | None, jd_text: str) -> bool:
    if not evidence_item:
        return False
    reference = evidence_item.get("source_reference", "")
    if any(marker in reference for marker in ["职位描述", "岗位描述", "核心职责", "岗位职责", "工作职责", "实习内容"]):
        return True
    header = re.search(r"(?:职位要求|岗位要求|任职要求|招聘要求)\s*[:：]", jd_text)
    if header is None:
        return False
    source = _compact(evidence_item.get("source_text"))
    if len(source) < 8:
        return False
    return source in _compact(jd_text[:header.start()]) and source not in _compact(jd_text[header.end():])


def _split_distinct_support_tasks(profile: dict[str, Any], changes: list[str]) -> None:
    tasks = {item["task_id"]: item for item in profile["tasks"]}
    result = []
    for cluster in profile["task_clusters"]:
        task_ids = cluster["task_ids"]
        if len(task_ids) < 2 or any(task_id not in tasks for task_id in task_ids):
            result.append(cluster)
            continue
        documentation = []
        training = []
        for task_id in task_ids:
            text = tasks[task_id]["normalized_task"] + tasks[task_id]["original_text"]
            if re.search(r"SOP|使用指南|演示模板|案例总结|标准化", text, re.I):
                documentation.append(task_id)
            elif re.search(r"培训|技术支持", text):
                training.append(task_id)
        if not documentation or not training or set(documentation + training) != set(task_ids):
            result.append(cluster)
            continue
        for suffix, name, selected in [
            ("-DOC", "案例沉淀与标准化复用", documentation),
            ("-TRAIN", "伙伴培训与技术支持", training),
        ]:
            selected_evidence = list(dict.fromkeys(
                evidence_id for task_id in selected for evidence_id in tasks[task_id]["evidence_ids"]
            ))
            result.append({
                "cluster_id": cluster["cluster_id"] + suffix,
                "cluster_name": name,
                "task_ids": selected,
                "importance": cluster["importance"],
                "rationale": "任务体验与偏好不同，分开判断。",
                "evidence_ids": selected_evidence,
            })
        changes.append("将案例/SOP沉淀与伙伴培训支持拆为两个任务簇")
    profile["task_clusters"] = result


def normalize_job_profile(profile: dict[str, Any], jd_text: str = "") -> list[str]:
    """Mutate only unambiguous fields and return a human-readable change log."""
    changes: list[str] = []
    evidence_items = {item["evidence_id"]: item for item in profile["evidence_registry"]}
    for capability in profile["capability_requirements"]:
        if jd_text and _evidence_from_duties(evidence_items.get(capability["evidence_id"]), jd_text):
            if capability["claim_type"] != "inferred" or capability["requirement_strength"] != "uncertain":
                capability["claim_type"] = "inferred"
                capability["requirement_strength"] = "uncertain"
                changes.append(f"职责推导的“{capability['capability_name']}”不是应聘硬门槛")
        if capability["claim_type"] == "inferred" and capability["requirement_strength"] != "uncertain":
            capability["requirement_strength"] = "uncertain"
            changes.append(f"推断能力“{capability['capability_name']}”的要求强度改为不确定")

    if jd_text:
        for tool in profile["tool_requirements"]:
            if _evidence_from_duties(evidence_items.get(tool["evidence_id"]), jd_text) and tool["requirement_strength"] != "role_context":
                tool["requirement_strength"] = "role_context"
                changes.append(f"职责中使用的工具“{tool['tool_name']}”标为工作场景")

    conditions = profile["basic_conditions"]
    degree = _compact(conditions["degree_requirements"]["minimum_degree"])
    kept = []
    for condition in conditions["other_application_conditions"]:
        value = _compact(condition["normalized_value"])
        if value and degree and (value in degree or degree in value):
            changes.append(f"移除与学历要求重复的条件“{condition['condition_name']}”")
        else:
            kept.append(condition)
    conditions["other_application_conditions"] = kept

    evidence = {item["evidence_id"]: item["source_text"] for item in profile["evidence_registry"]}
    days = conditions["days_per_week"]
    days_text = evidence.get(days["evidence_id"], "")
    if days["maximum"] is not None and "至少" in days_text and re.search(r"\d\s*[-—–至到]\s*\d", days_text):
        days["maximum"] = None
        changes.append("“至少 X–Y 天”未给出到岗上限，已将上限改为未知")

    duration = conditions["duration_months"]
    if duration["minimum"] is not None and duration["preferred"] == duration["minimum"]:
        duration["preferred"] = None
        changes.append("实习时长的偏好值与最低值重复，已移除未明确的偏好值")

    if jd_text:
        _split_distinct_support_tasks(profile, changes)
        work_style = profile["work_style"]
        independent = work_style["independent_analysis"]
        independent_evidence = " ".join(evidence.get(x, "") for x in independent["evidence_ids"])
        if independent["status"] == "known" and "独立" in str(independent["value"]) and not re.search(r"独立|自主负责", independent_evidence):
            independent.update({"status": "unknown", "value": None, "claim_type": "unknown", "evidence_ids": []})
            changes.append("JD 未明确独立负责范围，独立分析程度改为未知")
        technical = work_style["technical_depth"]
        technical_evidence = " ".join(evidence.get(x, "") for x in technical["evidence_ids"])
        if technical["status"] == "known" and re.search(r"非编程|无需编程|不需要编程", str(technical["value"])) and not re.search(r"非编程|无需编程|不需要编程", technical_evidence):
            technical.update({"status": "possible", "value": "涉及无代码/低代码配置，具体技术深度未知", "claim_type": "inferred"})
            changes.append("JD 未明确排除编程工作，技术深度改为待核验")
        travel = work_style["travel_or_client_site"]
        if travel["status"] == "known" and "可能" in str(travel["value"]):
            travel["status"] = "possible"
            travel["claim_type"] = "inferred"
            changes.append("客户现场或出差仅为可能，不写为已确认")
        research = work_style["research_vs_execution"]
        if research["status"] == "known" and re.search(r"并重|为主|偏向", str(research["value"])):
            research["status"] = "possible"
            research["claim_type"] = "inferred"
            changes.append("JD 未给出研究与执行时间占比，比例判断改为推断")

        work_markers = ("实习", "工作", "项目", "从业")
        kept_experience = []
        for experience in profile["experience_requirements"]:
            name = experience["experience_name"]
            if re.search(r"留学|院校|在读|学历|复合背景|专业", name) and not any(marker in name for marker in work_markers):
                changes.append(f"学历或教育背景“{name}”不计作既往工作经验")
            else:
                kept_experience.append(experience)
        profile["experience_requirements"] = kept_experience

        uncertainties = profile["job_uncertainties"]
        before_missing = len(uncertainties["missing_fields"])
        uncertainties["missing_fields"] = [
            item for item in uncertainties["missing_fields"] if not re.search(r"薪资|转正", item)
        ]
        if len(uncertainties["missing_fields"]) < before_missing:
            changes.append("首版岗位理解缺失项中移除薪资/转正噪声")
        before_sensitive = len(uncertainties["sensitive_requirements"])
        uncertainties["sensitive_requirements"] = [
            item for item in uncertainties["sensitive_requirements"]
            if not (re.search(r"20\d{2}届", item) and not re.search(r"性别|年龄|民族|婚育|籍贯", item))
        ]
        if len(uncertainties["sensitive_requirements"]) < before_sensitive:
            changes.append("招聘届别移出敏感偏好字段，保留在资格条件中")

    profile["job_uncertainties"]["warnings"].extend(
        f"系统归一化：{change}；请核对原始 JD。" for change in changes
    )
    return changes
