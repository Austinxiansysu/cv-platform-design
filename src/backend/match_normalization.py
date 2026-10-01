"""Narrow, auditable safeguards; unknown preferences never become dislikes."""

from __future__ import annotations

import re
from typing import Any


KNOWLEDGE_DOC = re.compile(r"SOP|使用指南|演示模板|方案模板|知识总结|案例沉淀", re.I)
DIRECT_DOC = re.compile(r"SOP|使用指南|演示|模板|知识总结|方案|培训", re.I)
ARCHIVE = re.compile(r"档案|合规")


def normalize_match_alignment(
    profile: dict[str, Any], job: dict[str, Any], alignment: dict[str, Any]
) -> list[str]:
    """Change only recognizable over-generalization, preserving a warning trail."""
    evidence = {item["evidence_id"]: item["source_text"] for item in profile["evidence_registry"]}
    clusters = {item["cluster_id"]: item for item in job["task_clusters"]}
    changes = []
    for capability in alignment["capability_alignments"]:
        if capability["status"] == "not_demonstrated" and capability["gap_type"] != "evidence_gap":
            capability["gap_type"] = "evidence_gap"
            changes.append(f"能力{capability['job_capability_id']}：未证明归为证据缺口，不归为确认能力缺口")

    gaps = alignment["gap_summary"]
    kept = []
    for gap in gaps["structural_feasibility_gaps"]:
        uncertain = any(word in gap for word in ["未知", "无法判断", "可能"])
        confirmed_conflict = any(word in gap for word in ["不符", "不满足", "无法满足", "超出", "冲突", "不能满足"])
        if uncertain and not confirmed_conflict:
            if gap not in gaps["information_gaps"]:
                gaps["information_gaps"].append(gap)
            changes.append("将未知或可能的条件从确定结构缺口移入信息缺口")
        else:
            kept.append(gap)
    gaps["structural_feasibility_gaps"] = kept
    corrected_preference = False
    for item in alignment["task_alignments"]:
        cluster = clusters.get(item["job_task_cluster_id"])
        ids = item["preference_evidence_ids"]
        if not cluster or item["preference_alignment"] != "negative" or not ids:
            continue
        # Never hide an invalid evidence ID by removing it during normalization.
        if any(identifier not in evidence for identifier in ids):
            continue
        sources = [evidence[identifier] for identifier in ids]
        if not KNOWLEDGE_DOC.search(cluster["cluster_name"]):
            continue
        if not all(ARCHIVE.search(source) and not DIRECT_DOC.search(source) for source in sources):
            continue
        item.update({
            "preference_alignment": "untested",
            "preference_evidence_ids": [],
            "preference_risk": "方案SOP与模板沉淀偏好尚未验证，不能由合规档案整理偏好直接推断。",
            "explanation": "偏好证据仅涉及合规或档案整理，不直接支持本任务的负面偏好；能力证据保留，偏好改为未验证。",
            "confidence": "low",
        })
        corrected_preference = True
        changes.append(f"任务{item['job_task_cluster_id']}：撤销由合规档案整理推广出的方案文档负面偏好，改为未验证")

    if corrected_preference:
        explanation = alignment["user_facing_explanation"]
        reminder = "方案SOP与模板沉淀偏好尚未验证，不从合规档案整理偏好直接推断。"
        for values in (explanation["main_risks"], alignment["gap_summary"]["preference_risks"]):
            values[:] = list(dict.fromkeys(reminder if KNOWLEDGE_DOC.search(value) else value for value in values))
        explanation["one_sentence_conclusion"] = "已纠正任务偏好的过度推广；未验证任务不计偏好分，请结合下方支持点与信息缺口判断。当前申请资格单独显示。"
    if changes:
        warnings = alignment["match_meta"]["warnings"]
        for change in changes:
            warning = "系统证据校验：" + change
            if warning not in warnings:
                warnings.append(warning)
    return changes
