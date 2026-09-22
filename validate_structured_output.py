import argparse
import json
import re
from pathlib import Path


def validate_schema(schema, data, path="$", errors=None):
    errors = errors if errors is not None else []
    if "anyOf" in schema:
        branch_errors = []
        for branch in schema["anyOf"]:
            candidate = []
            validate_schema(branch, data, path, candidate)
            branch_errors.append(candidate)
        if all(branch_errors):
            errors.append({"severity": "P0", "type": "schema", "path": path, "message": "No anyOf branch matched"})
        return errors

    expected = schema.get("type")
    checks = {
        "object": lambda value: isinstance(value, dict),
        "array": lambda value: isinstance(value, list),
        "string": lambda value: isinstance(value, str),
        "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
        "boolean": lambda value: isinstance(value, bool),
        "null": lambda value: value is None,
    }
    if expected in checks and not checks[expected](data):
        errors.append({"severity": "P0", "type": "schema", "path": path, "message": f"Expected {expected}, got {type(data).__name__}"})
        return errors
    if "enum" in schema and data not in schema["enum"]:
        errors.append({"severity": "P0", "type": "schema", "path": path, "message": f"Invalid enum value {data!r}"})

    if expected == "object":
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in data:
                errors.append({"severity": "P0", "type": "schema", "path": path, "message": f"Missing required field {key}"})
        if schema.get("additionalProperties") is False:
            for key in data:
                if key not in properties:
                    errors.append({"severity": "P0", "type": "schema", "path": path, "message": f"Unexpected field {key}"})
        for key, value in data.items():
            if key in properties:
                validate_schema(properties[key], value, f"{path}.{key}", errors)
    elif expected == "array":
        for index, value in enumerate(data):
            validate_schema(schema["items"], value, f"{path}[{index}]", errors)
    return errors


def collect_references(value, parent_key="", refs=None):
    refs = refs if refs is not None else []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "evidence_id" and item is not None:
                refs.append(item)
            elif key == "evidence_ids":
                refs.extend(item)
            elif key != "evidence_registry":
                collect_references(item, key, refs)
    elif isinstance(value, list):
        for item in value:
            collect_references(item, parent_key, refs)
    return refs


def semantic_job_checks(data, errors):
    evidence_registry = data.get("evidence_registry", [])
    evidence_ids = {item["evidence_id"] for item in evidence_registry}
    evidence_index = {item["evidence_id"]: item for item in evidence_registry}
    for evidence_id in collect_references(data):
        if evidence_id not in evidence_ids:
            errors.append({"severity": "P0", "type": "broken_evidence_reference", "path": "$", "message": f"Unknown evidence_id {evidence_id}"})

    task_ids = {item["task_id"] for item in data.get("tasks", [])}
    for cluster in data.get("task_clusters", []):
        for task_id in cluster["task_ids"]:
            if task_id not in task_ids:
                errors.append({"severity": "P0", "type": "broken_task_reference", "path": f"$.task_clusters.{cluster['cluster_id']}", "message": f"Unknown task_id {task_id}"})

    for cap in data.get("capability_requirements", []):
        if cap["claim_type"] == "inferred" and cap["requirement_strength"] != "uncertain":
            errors.append({"severity": "P1", "type": "over_inference", "path": f"$.capability_requirements.{cap['capability_id']}", "message": "Inferred capability must use uncertain strength"})

    if any("远程面试" in location for location in data.get("basic_conditions", {}).get("locations", [])):
        errors.append({"severity": "P1", "type": "field_misclassification", "path": "$.basic_conditions.locations", "message": "Interview mode used as work location"})

    degree_text = str(data.get("basic_conditions", {}).get("degree_requirements", {}).get("minimum_degree") or "")
    for index, condition in enumerate(data.get("basic_conditions", {}).get("other_application_conditions", [])):
        normalized = condition.get("normalized_value", "")
        if normalized and degree_text and (normalized in degree_text or degree_text in normalized):
            errors.append({"severity": "P2", "type": "duplicate_fact", "path": f"$.basic_conditions.other_application_conditions[{index}]", "message": "Condition duplicates degree_requirements"})

    days = data.get("basic_conditions", {}).get("days_per_week", {})
    days_evidence = evidence_index.get(days.get("evidence_id"), {})
    days_text = days_evidence.get("source_text", "")
    if (
        days.get("maximum") is not None
        and "至少" in days_text
        and re.search(r"\d\s*[-—–至到]\s*\d", days_text)
    ):
        errors.append({
            "severity": "P1",
            "type": "ambiguous_minimum_range",
            "path": "$.basic_conditions.days_per_week.maximum",
            "message": "A phrase such as 'at least X-Y days' does not establish a hard maximum; keep maximum null and request confirmation",
        })

    duration = data.get("basic_conditions", {}).get("duration_months", {})
    if (
        duration.get("minimum") is not None
        and duration.get("preferred") == duration.get("minimum")
    ):
        errors.append({
            "severity": "P2",
            "type": "duplicate_duration_preference",
            "path": "$.basic_conditions.duration_months.preferred",
            "message": "Preferred duration duplicates the minimum; use null unless the JD states a distinct preference",
        })


def semantic_profile_checks(data, errors):
    for index, preference in enumerate(data.get("task_preferences", [])):
        if preference["preference_level"] == "untested" and preference["status"] != "untested":
            errors.append({"severity": "P1", "type": "preference_status", "path": f"$.task_preferences[{index}]", "message": "Untested preference must use status=untested"})
        if preference["preference_level"] == "untested" and preference["confidence"] != "low":
            errors.append({"severity": "P1", "type": "preference_confidence", "path": f"$.task_preferences[{index}]", "message": "Untested preference must use low preference confidence"})
    for index, skill in enumerate(data.get("skills", [])):
        if "兴趣" in skill["skill_name"]:
            errors.append({"severity": "P1", "type": "interest_as_skill", "path": f"$.skills[{index}]", "message": "Interest must not be stored as a skill"})
    for index, gap in enumerate(data.get("profile_gaps", {}).get("confirmed_skill_gaps", [])):
        if any(marker in gap for marker in ["尚未体验", "尚未真实体验", "未体验", "没有证据", "未证明"]):
            errors.append({"severity": "P1", "type": "untested_as_confirmed_gap", "path": f"$.profile_gaps.confirmed_skill_gaps[{index}]", "message": "Untested or unproven item is not a confirmed skill gap"})


def semantic_match_checks(data, errors):
    eligibility = data.get("current_application_eligibility", {})
    status = eligibility.get("status")
    unknown_text = " ".join(eligibility.get("unknown_conditions", []))
    snapshot_text = " ".join(eligibility.get("time_snapshot_conditions", []))
    conflict_text = " ".join(eligibility.get("conflicting_conditions", []))
    if (
        status == "pass"
        and any(marker in snapshot_text for marker in ["寒暑假", "学期中"])
        and any(marker in unknown_text for marker in ["最早开始", "开始时间", "实习时段", "到岗日期"])
    ):
        errors.append({
            "severity": "P1",
            "type": "unresolved_timing_marked_pass",
            "path": "$.current_application_eligibility.status",
            "message": "Holiday-only availability plus an unknown start window must remain pending",
        })
    if status == "current_cycle_conflict" and any(
        marker in conflict_text for marker in ["未核验", "未知", "未说明", "需确认"]
    ):
        errors.append({
            "severity": "P1",
            "type": "unknown_timing_marked_conflict",
            "path": "$.current_application_eligibility.conflicting_conditions",
            "message": "An unverified schedule is pending information, not a confirmed current-cycle conflict",
        })
    if status == "pending" and any(
        marker in snapshot_text for marker in ["超出", "不满足", "不符", "冲突"]
    ):
        errors.append({
            "severity": "P1",
            "type": "confirmed_timing_conflict_marked_pending",
            "path": "$.current_application_eligibility.status",
            "message": "A confirmed current-cycle timing mismatch takes precedence over other unknown conditions",
        })
    for index, alignment in enumerate(data.get("capability_alignments", [])):
        if alignment["status"] == "not_demonstrated" and alignment["gap_type"] != "evidence_gap":
            errors.append({"severity": "P1", "type": "unproven_as_capability_gap", "path": f"$.capability_alignments[{index}]", "message": "not_demonstrated must use evidence_gap"})
    for index, gap in enumerate(data.get("gap_summary", {}).get("structural_feasibility_gaps", [])):
        if any(marker in gap for marker in ["未知", "无法判断", "可能"]):
            errors.append({"severity": "P1", "type": "unknown_as_structural_gap", "path": f"$.gap_summary.structural_feasibility_gaps[{index}]", "message": "Unknown or possible condition is not a confirmed structural gap"})
        if "当前学历" in gap:
            errors.append({"severity": "P1", "type": "current_state_as_structural_gap", "path": f"$.gap_summary.structural_feasibility_gaps[{index}]", "message": "Current education stage is time-varying; do not label it structural without a confirmed long-term education constraint"})
    for index, gap in enumerate(data.get("gap_summary", {}).get("capability_gaps", [])):
        if any(marker in gap for marker in ["尚未体验", "尚未真实体验", "未体验", "没有证据", "未证明"]):
            errors.append({"severity": "P1", "type": "unproven_as_capability_gap", "path": f"$.gap_summary.capability_gaps[{index}]", "message": "Untested or unproven item is not a confirmed capability gap"})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    parser.add_argument("--kind", choices=["job", "profile", "match"], required=True)
    args = parser.parse_args()

    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    errors = validate_schema(schema, data)
    if args.kind == "job" and not any(item["severity"] == "P0" for item in errors):
        semantic_job_checks(data, errors)
    if args.kind == "profile" and not any(item["severity"] == "P0" for item in errors):
        semantic_profile_checks(data, errors)
    if args.kind == "match" and not any(item["severity"] == "P0" for item in errors):
        semantic_match_checks(data, errors)

    result = {
        "input": args.input,
        "valid": not errors,
        "p0_count": sum(item["severity"] == "P0" for item in errors),
        "p1_count": sum(item["severity"] == "P1" for item in errors),
        "p2_count": sum(item["severity"] == "P2" for item in errors),
        "errors": errors,
    }
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text, end="")
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
