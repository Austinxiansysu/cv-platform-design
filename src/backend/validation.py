"""Validate frozen structured outputs before they enter the local database."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from validate_structured_output import (
    semantic_job_checks,
    semantic_match_checks,
    semantic_profile_checks,
)


SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"
SCHEMA_FILES = {
    "profile": "profile.output.schema.json",
    "job": "job_profile.output.schema.json",
    "match": "match_alignment.output.schema.json",
}


@lru_cache(maxsize=3)
def _validator(kind: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / SCHEMA_FILES[kind]).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_payload(kind: str, payload: dict[str, Any]) -> list[dict[str, str]]:
    errors = [
        {
            "severity": "P0",
            "type": "schema",
            "path": "$" + "".join(f"[{part!r}]" for part in error.absolute_path),
            "message": error.message,
        }
        for error in _validator(kind).iter_errors(payload)
    ]
    if errors:
        return errors

    checks = {
        "profile": semantic_profile_checks,
        "job": semantic_job_checks,
        "match": semantic_match_checks,
    }
    checks[kind](payload, errors)
    return errors


def validate_match_references(
    profile: dict[str, Any], job: dict[str, Any], alignment: dict[str, Any]
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    expected_tasks = {item["cluster_id"] for item in job["task_clusters"]}
    actual_tasks = {item["job_task_cluster_id"] for item in alignment["task_alignments"]}
    if expected_tasks != actual_tasks or len(actual_tasks) != len(alignment["task_alignments"]):
        errors.append({
            "severity": "P0",
            "type": "task_alignment_mismatch",
            "path": "$.task_alignments",
            "message": "Task alignments must cover each job task cluster exactly once",
        })
    expected_caps = {item["capability_id"] for item in job["capability_requirements"]}
    actual_caps = {item["job_capability_id"] for item in alignment["capability_alignments"]}
    if expected_caps != actual_caps or len(actual_caps) != len(alignment["capability_alignments"]):
        errors.append({
            "severity": "P0",
            "type": "capability_alignment_mismatch",
            "path": "$.capability_alignments",
            "message": "Capability alignments must cover each job capability exactly once",
        })
    meta = alignment["match_meta"]
    if meta["profile_version"] != profile["profile_meta"]["profile_version"]:
        errors.append({
            "severity": "P0",
            "type": "profile_version_mismatch",
            "path": "$.match_meta.profile_version",
            "message": "Match profile version differs from the stored profile",
        })
    if meta["job_id"] != job["job_meta"]["job_id"]:
        errors.append({
            "severity": "P0",
            "type": "job_id_mismatch",
            "path": "$.match_meta.job_id",
            "message": "Match job ID differs from the stored job",
        })
    profile_evidence_ids = {item["evidence_id"] for item in profile["evidence_registry"]}
    registry_ids = [item["evidence_id"] for item in alignment["profile_evidence_registry"]]
    cited_ids: set[str] = set()
    for task in alignment["task_alignments"]:
        cited_ids.update(task["preference_evidence_ids"])
        cited_ids.update(task["readiness_evidence_ids"])
    for capability in alignment["capability_alignments"]:
        cited_ids.update(capability["user_evidence_ids"])
    if (
        cited_ids - profile_evidence_ids
        or cited_ids - set(registry_ids)
        or set(registry_ids) - profile_evidence_ids
        or len(registry_ids) != len(set(registry_ids))
    ):
        errors.append({
            "severity": "P0",
            "type": "profile_evidence_mismatch",
            "path": "$.profile_evidence_registry",
            "message": "Cited profile evidence must exist in the stored profile and match registry",
        })
    return errors
