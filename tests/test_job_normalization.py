import copy
import json
import unittest
from pathlib import Path

from src.backend.job_normalization import normalize_job_profile
from src.backend.validation import validate_payload


ROOT = Path(__file__).resolve().parents[1]


class JobNormalizationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
