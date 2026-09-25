"""Evidence-bound resume wording drafts without adding new claims."""

from __future__ import annotations

from typing import Any


def _distinct(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def build_resume_advice(
    profile: dict[str, Any], job: dict[str, Any], alignment: dict[str, Any]
) -> dict[str, Any]:
    """Use only confirmed experience facts; job suggestions choose emphasis, not facts."""
    confirmation = profile["profile_meta"]["confirmation_status"]
    focus_candidates = alignment["user_facing_explanation"]["resume_focus_candidates"]
    global_prohibited = alignment["user_facing_explanation"]["prohibited_resume_additions"]
    suggestions = []
    needs_more_information = []

    for experience in profile["experiences"]:
        actions = _distinct(experience["user_actions"])
        deliverables = _distinct(experience["deliverables"])
        identifier = experience["experience_id"]
        title = experience["title"]
        if confirmation == "unconfirmed" or (confirmation == "partially_confirmed" and experience["confirmation_needed"]):
            needs_more_information.append({
                "experience_id": identifier,
                "title": title,
                "reason": "这段经历尚未由用户确认，先核对事实。",
            })
            continue
        if not actions or not deliverables:
            needs_more_information.append({
                "experience_id": identifier,
                "title": title,
                "reason": "缺少具体行动或交付物，无法生成有证据的简历句子。",
            })
            continue

        focus = [
            item for item in focus_candidates
            if title in item or any(tool and tool in item for tool in experience["tools"])
        ]
        sentence = f"{title}：{'；'.join(actions)}，形成{'、'.join(deliverables)}。"
        warnings = []
        if experience["confirmation_needed"]:
            warnings.append("日期、结果或证明材料可能仍需补充；此句只使用已列行动与交付物。")
        suggestions.append({
            "experience_id": identifier,
            "title": title,
            "source_actions": actions,
            "source_deliverables": deliverables,
            "source_evidence_ids": experience["evidence_ids"],
            "suggested_sentence": sentence,
            "job_focus": focus,
            "warnings": warnings,
            "prohibited_claims": _distinct(experience["prohibited_claims"] + global_prohibited),
            "requires_user_review": True,
        })

    suggestions.sort(key=lambda item: (-len(item["job_focus"]), item["experience_id"]))
    return {
        "profile_version": profile["profile_meta"]["profile_version"],
        "job_id": job["job_meta"]["job_id"],
        "match_id": alignment["match_meta"]["match_id"],
        "suggestions": suggestions,
        "needs_more_information": needs_more_information,
        "notice": "建议句只组合已确认行动与交付物；岗位重点不自动写入经历，使用前仍须本人核对。",
    }
