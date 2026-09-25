import copy
import json
import unittest
from pathlib import Path

from src.backend.job_normalization import normalize_job_profile, normalize_pre_schema
from src.backend.validation import validate_payload


ROOT = Path(__file__).resolve().parents[1]


class JobNormalizationTests(unittest.TestCase):
    def test_unknown_requirement_strength_maps_to_uncertain(self):
        payload = {"basic_conditions": {"degree_requirements": {
            "status": "unknown", "requirement_strength": "unknown",
        }}}
        changes = normalize_pre_schema(payload)
        self.assertEqual(len(changes), 1)
        self.assertEqual(payload["basic_conditions"]["degree_requirements"]["requirement_strength"], "uncertain")

    def test_known_mechanical_errors_are_corrected_and_logged(self):
        job = json.loads(
            (ROOT / "fixtures" / "fde_job_profile_expected.json").read_text(encoding="utf-8")
        )
        job = copy.deepcopy(job)
        initial_warning_count = len(job["job_uncertainties"]["warnings"])
        capability = job["capability_requirements"][0]
        capability["claim_type"] = "inferred"
        capability["requirement_strength"] = "must"
        conditions = job["basic_conditions"]
        conditions["other_application_conditions"].append({
            "condition_name": "学历", "normalized_value": "本科",
            "requirement_strength": "must", "gate_type": "hard_gate",
            "evidence_id": "J07-E01",
        })
        conditions["days_per_week"].update({
            "status": "known", "minimum": 1, "maximum": 2, "evidence_id": "J07-E01",
        })
        conditions["duration_months"].update({
            "status": "known", "minimum": 3, "preferred": 3, "evidence_id": "J07-E01",
        })
        next(item for item in job["evidence_registry"] if item["evidence_id"] == "J07-E01")["source_text"] = "每周至少1-2天"

        changes = normalize_job_profile(job)

        self.assertEqual(len(changes), 4)
        self.assertEqual(capability["requirement_strength"], "uncertain")
        self.assertEqual(conditions["other_application_conditions"], [])
        self.assertIsNone(conditions["days_per_week"]["maximum"])
        self.assertIsNone(conditions["duration_months"]["preferred"])
        self.assertEqual(len(job["job_uncertainties"]["warnings"]), initial_warning_count + 4)
        self.assertEqual(validate_payload("job", job), [])

    def test_duties_are_not_applicant_hard_gates_and_distinct_tasks_split(self):
        job = json.loads(
            (ROOT / "fixtures" / "fde_job_profile_expected.json").read_text(encoding="utf-8")
        )
        job = copy.deepcopy(job)
        capability = job["capability_requirements"][0]
        capability.update({
            "capability_name": "客户调研能力",
            "claim_type": "explicit",
            "requirement_strength": "must",
            "evidence_id": "J07-E03",
        })
        next(item for item in job["evidence_registry"] if item["evidence_id"] == "J07-E03")["source_reference"] = "职位描述-2"
        documentation = job["task_clusters"][2]
        training = job["task_clusters"][3]
        documentation["task_ids"].extend(training["task_ids"])
        documentation["evidence_ids"].extend(training["evidence_ids"])
        job["task_clusters"] = job["task_clusters"][:3]

        jd_text = (ROOT / "eval_inputs" / "fde_job_prompt_v1.txt").read_text(encoding="utf-8").split("原始 JD：", 1)[1]
        changes = normalize_job_profile(job, jd_text)

        self.assertEqual(capability["claim_type"], "inferred")
        self.assertEqual(capability["requirement_strength"], "uncertain")
        self.assertEqual(len(job["task_clusters"]), 4)
        self.assertTrue(any("伙伴培训" in cluster["cluster_name"] for cluster in job["task_clusters"]))
        self.assertTrue(any("拆为两个任务簇" in change for change in changes))
        self.assertEqual(validate_payload("job", job), [])

    def test_live_regression_edges_keep_cohorts_skills_and_industry_separate(self):
        job = json.loads(
            (ROOT / "fixtures" / "fde_job_profile_expected.json").read_text(encoding="utf-8")
        )
        job = copy.deepcopy(job)
        job["basic_conditions"]["graduation_cohorts"].update({
            "status": "known", "values": ["应届"],
            "requirement_strength": "must", "evidence_id": "J07-E01",
        })
        capability = job["capability_requirements"][0]
        capability.update({
            "capability_name": "SQL", "original_text": "掌握SQL、Python和A/B实验",
            "claim_type": "explicit", "requirement_strength": "uncertain",
        })
        job["job_meta"]["company"] = "中金财富"
        job["relevance_dimensions"]["finance_relevance"].update({
            "level": 2, "evidence_ids": ["J07-E01"],
        })
        job["tool_requirements"][0].update({
            "tool_name": "BI报表工具", "original_text": "熟悉BI报表方法",
            "requirement_strength": "must",
        })

        changes = normalize_job_profile(job, "任职要求：掌握SQL、Python和A/B实验")

        self.assertEqual(job["basic_conditions"]["graduation_cohorts"]["status"], "unknown")
        self.assertEqual(job["basic_conditions"]["graduation_cohorts"]["values"], [])
        self.assertEqual(capability["requirement_strength"], "must")
        self.assertEqual(job["relevance_dimensions"]["finance_relevance"]["level"], 1)
        self.assertNotIn("BI报表工具", [tool["tool_name"] for tool in job["tool_requirements"]])
        self.assertTrue(any("明确要求掌握" in change for change in changes))


if __name__ == "__main__":
    unittest.main()
