"""Auditable, mechanical corrections for recurring JD extraction mistakes."""

from __future__ import annotations

import re
from typing import Any


def _compact(value: Any) -> str:
    return "".join(str(value or "").lower().split()).replace("；", "").replace("，", "")


def normalize_job_profile(profile: dict[str, Any]) -> list[str]:
    """Mutate only unambiguous fields and return a human-readable change log."""
    changes: list[str] = []
    for capability in profile["capability_requirements"]:
        if capability["claim_type"] == "inferred" and capability["requirement_strength"] != "uncertain":
            capability["requirement_strength"] = "uncertain"
            changes.append(f"推断能力“{capability['capability_name']}”的要求强度改为不确定")

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

    profile["job_uncertainties"]["warnings"].extend(
        f"系统归一化：{change}；请核对原始 JD。" for change in changes
    )
    return changes
