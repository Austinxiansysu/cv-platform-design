"""Deterministic scoring for validated profile-to-job alignment data.

The language model extracts evidence and alignment states. This module converts
those fixed states into transparent scores. It never invents missing values and
keeps current application eligibility separate from career-direction fit.
"""

from __future__ import annotations

from typing import Any, Iterable


IMPORTANCE_WEIGHTS = {
    "core": 3.0,
    "important_support": 2.0,
    "general_support": 1.0,
}

PREFERENCE_SCORES = {
    "positive": 100.0,
    "neutral": 50.0,
    "negative": 0.0,
}

TASK_READINESS_SCORES = {
    "direct_strong": 100.0,
    "direct_basic": 75.0,
    "transferable": 50.0,
    "self_report_only": 25.0,
    "not_demonstrated": 0.0,
    "confirmed_gap": 0.0,
}

CAPABILITY_READINESS_SCORES = {
    "supported": 100.0,
    "partially_supported": 50.0,
    "not_demonstrated": 0.0,
    "confirmed_gap": 0.0,
}

CAPABILITY_WEIGHTS = {
    "must": 3.0,
    "preferred": 1.0,
    "role_context": 1.0,
    "background": 1.0,
    "uncertain": 1.0,
}

EXPLORATION_SCORES = {
    "high": 100.0,
    "medium": 70.0,
    "low": 30.0,
}

MIN_PREFERENCE_COVERAGE = 0.50


def _weighted_average(items: Iterable[tuple[float, float]]) -> float | None:
    pairs = list(items)
    total_weight = sum(weight for _, weight in pairs)
    if total_weight == 0:
        return None
    return sum(value * weight for value, weight in pairs) / total_weight


def _round_to_five(value: float | None) -> int | None:
    if value is None:
        return None
    return int(5 * round(value / 5))


def _index_by(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        identifier = item[key]
        if identifier in result:
            raise ValueError(f"Duplicate {key}: {identifier}")
        result[identifier] = item
    return result


def _preference_score(
    task_clusters: list[dict[str, Any]],
    task_alignments: list[dict[str, Any]],
) -> tuple[float | None, float]:
    cluster_index = _index_by(task_clusters, "cluster_id")
    alignment_index = _index_by(task_alignments, "job_task_cluster_id")

    total_weight = sum(IMPORTANCE_WEIGHTS[item["importance"]] for item in task_clusters)
    known_weight = 0.0
    scored: list[tuple[float, float]] = []

    for cluster_id, cluster in cluster_index.items():
        alignment = alignment_index.get(cluster_id)
        if alignment is None:
            continue
        state = alignment["preference_alignment"]
        if state == "untested":
            continue
        if state not in PREFERENCE_SCORES:
            raise ValueError(f"Unknown preference alignment: {state}")
        weight = IMPORTANCE_WEIGHTS[cluster["importance"]]
        known_weight += weight
        scored.append((PREFERENCE_SCORES[state], weight))

    coverage = known_weight / total_weight if total_weight else 0.0
    if coverage < MIN_PREFERENCE_COVERAGE:
        return None, coverage
    return _weighted_average(scored), coverage


def _task_readiness_score(
    task_clusters: list[dict[str, Any]],
    task_alignments: list[dict[str, Any]],
) -> tuple[float | None, float]:
    cluster_index = _index_by(task_clusters, "cluster_id")
    alignment_index = _index_by(task_alignments, "job_task_cluster_id")
    total_weight = sum(IMPORTANCE_WEIGHTS[item["importance"]] for item in task_clusters)
    known_weight = 0.0
    scored: list[tuple[float, float]] = []

    for cluster_id, cluster in cluster_index.items():
        alignment = alignment_index.get(cluster_id)
        if alignment is None:
            continue
        level = alignment["readiness_evidence_level"]
        if level == "unknown":
            continue
        if level not in TASK_READINESS_SCORES:
            raise ValueError(f"Unknown task readiness level: {level}")
        weight = IMPORTANCE_WEIGHTS[cluster["importance"]]
        known_weight += weight
        scored.append((TASK_READINESS_SCORES[level], weight))

    coverage = known_weight / total_weight if total_weight else 0.0
    return _weighted_average(scored), coverage


def _capability_readiness_score(
    capability_requirements: list[dict[str, Any]],
    capability_alignments: list[dict[str, Any]],
) -> tuple[float | None, float]:
    requirement_index = _index_by(capability_requirements, "capability_id")
    alignment_index = _index_by(capability_alignments, "job_capability_id")
    total_weight = sum(
        CAPABILITY_WEIGHTS[item["requirement_strength"]]
        for item in capability_requirements
    )
    known_weight = 0.0
    scored: list[tuple[float, float]] = []

    for capability_id, requirement in requirement_index.items():
        alignment = alignment_index.get(capability_id)
        if alignment is None:
            continue
        state = alignment["status"]
        if state == "unknown":
            continue
        if state not in CAPABILITY_READINESS_SCORES:
            raise ValueError(f"Unknown capability alignment: {state}")
        weight = CAPABILITY_WEIGHTS[requirement["requirement_strength"]]
        known_weight += weight
        scored.append((CAPABILITY_READINESS_SCORES[state], weight))

    coverage = known_weight / total_weight if total_weight else 0.0
    return _weighted_average(scored), coverage


def _combine_readiness(
    task_score: float | None,
    capability_score: float | None,
) -> float | None:
    available: list[tuple[float, float]] = []
    if task_score is not None:
        available.append((task_score, 0.60))
    if capability_score is not None:
        available.append((capability_score, 0.40))
    return _weighted_average(available)


def _exploration_score(assessment: dict[str, Any]) -> tuple[float | None, float]:
    values = [
        (assessment["direction_alignment"], 0.40),
        (assessment["growth_value"], 0.60),
    ]
    scored: list[tuple[float, float]] = []
    known_weight = 0.0
    for state, weight in values:
        if state == "unknown":
            continue
        if state not in EXPLORATION_SCORES:
            raise ValueError(f"Unknown exploration value: {state}")
        known_weight += weight
        scored.append((EXPLORATION_SCORES[state], weight))
    return _weighted_average(scored), known_weight


def _direction_label(
    desire_score: float | None,
    assessment: dict[str, Any],
) -> str:
    direction = assessment["direction_alignment"]
    if desire_score is not None and desire_score < 50:
        return "low_priority_direction"
    if direction == "high" and desire_score is not None and desire_score >= 75:
        return "priority_direction"
    if direction in {"high", "medium"}:
        return "worth_exploring"
    if direction == "low":
        return "low_priority_direction"
    return "needs_more_experience"


def _action_label(
    eligibility_status: str,
    overall_score: int | None,
    desire_score: float | None,
    readiness_score: float | None,
) -> str:
    if eligibility_status == "current_cycle_conflict":
        return "save_job_archetype"
    if eligibility_status == "structural_conflict":
        return "not_recommended_now"
    if eligibility_status == "pending":
        return "gather_information"
    if eligibility_status != "pass":
        raise ValueError(f"Unknown eligibility status: {eligibility_status}")
    if overall_score is None:
        return "explore_before_applying"
    if overall_score >= 80 and (readiness_score or 0) >= 60:
        return "priority_apply"
    if (desire_score or 0) >= 75 and (readiness_score or 0) < 60:
        return "stretch_apply"
    if overall_score >= 65:
        return "worth_applying"
    return "low_priority"


def _result_confidence(
    preference_coverage: float,
    task_readiness_coverage: float,
    capability_readiness_coverage: float,
    exploration_coverage: float,
    assessment_confidence: str,
    input_status: str,
) -> str:
    if preference_coverage < 0.50:
        return "low"
    average_coverage = (
        preference_coverage
        + task_readiness_coverage
        + capability_readiness_coverage
        + exploration_coverage
    ) / 4
    if (
        average_coverage >= 0.80
        and assessment_confidence == "high"
        and input_status == "sufficient"
    ):
        return "high"
    if average_coverage >= 0.50:
        return "medium"
    return "low"


def score_match(
    job_profile: dict[str, Any],
    match_alignment: dict[str, Any],
) -> dict[str, Any]:
    """Return transparent scores and labels without changing either input."""

    desire_score, preference_coverage = _preference_score(
        job_profile["task_clusters"], match_alignment["task_alignments"]
    )
    task_readiness_score, task_readiness_coverage = _task_readiness_score(
        job_profile["task_clusters"], match_alignment["task_alignments"]
    )
    capability_readiness_score, capability_readiness_coverage = (
        _capability_readiness_score(
            job_profile["capability_requirements"],
            match_alignment["capability_alignments"],
        )
    )
    readiness_score = _combine_readiness(
        task_readiness_score, capability_readiness_score
    )
    assessment = match_alignment["career_direction_assessment"]
    exploration_score, exploration_coverage = _exploration_score(assessment)

    overall_raw = None
    if (
        desire_score is not None
        and readiness_score is not None
        and exploration_score is not None
    ):
        overall_raw = (
            desire_score * 0.45
            + readiness_score * 0.30
            + exploration_score * 0.25
        )
    overall_score = _round_to_five(overall_raw)
    eligibility_status = match_alignment["current_application_eligibility"]["status"]

    return {
        "desire_score": None if desire_score is None else round(desire_score, 2),
        "preference_coverage": round(preference_coverage, 4),
        "task_readiness_score": None if task_readiness_score is None else round(task_readiness_score, 2),
        "task_readiness_coverage": round(task_readiness_coverage, 4),
        "capability_readiness_score": None if capability_readiness_score is None else round(capability_readiness_score, 2),
        "capability_readiness_coverage": round(capability_readiness_coverage, 4),
        "readiness_score": None if readiness_score is None else round(readiness_score, 2),
        "exploration_score": None if exploration_score is None else round(exploration_score, 2),
        "exploration_coverage": round(exploration_coverage, 4),
        "career_direction_summary": overall_score,
        "career_direction_label": _direction_label(desire_score, assessment),
        "current_application_status": eligibility_status,
        "current_action_label": _action_label(
            eligibility_status, overall_score, desire_score, readiness_score
        ),
        "result_confidence": _result_confidence(
            preference_coverage,
            task_readiness_coverage,
            capability_readiness_coverage,
            exploration_coverage,
            assessment["confidence"],
            match_alignment["match_meta"]["input_status"],
        ),
    }
