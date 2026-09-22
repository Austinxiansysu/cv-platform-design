import copy
import json
import unittest
from pathlib import Path

from src.matching.scoring import score_match


ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


class ScoringTests(unittest.TestCase):
    def test_fde_low_preference_coverage_suppresses_total_score(self):
        result = score_match(
            load_json("fixtures/fde_job_profile_expected.json"),
            load_json("fixtures/fde_match_expected.json"),
        )
        self.assertEqual(result["preference_coverage"], 0.3)
        self.assertIsNone(result["desire_score"])
        self.assertIsNone(result["career_direction_summary"])
        self.assertEqual(result["career_direction_label"], "worth_exploring")
        self.assertEqual(result["current_action_label"], "save_job_archetype")
        self.assertEqual(result["result_confidence"], "low")

    def test_tencent_has_enough_preference_coverage_for_summary(self):
        result = score_match(
            load_json("fixtures/tencent_business_analysis_job_profile_expected.json"),
            load_json("fixtures/tencent_business_analysis_match_expected.json"),
        )
        self.assertAlmostEqual(result["preference_coverage"], 8 / 13, places=4)
        self.assertEqual(result["desire_score"], 87.5)
        self.assertAlmostEqual(result["readiness_score"], 40.38, places=2)
        self.assertEqual(result["exploration_score"], 100.0)
        self.assertEqual(result["career_direction_summary"], 75)
        self.assertEqual(result["career_direction_label"], "priority_direction")
        self.assertEqual(result["current_action_label"], "gather_information")

    def test_current_cycle_conflict_does_not_change_direction_metrics(self):
        job = load_json("fixtures/fde_job_profile_expected.json")
        match = load_json("fixtures/fde_match_expected.json")
        conflicted = score_match(job, match)
        passed_match = copy.deepcopy(match)
        passed_match["current_application_eligibility"]["status"] = "pass"
        passed = score_match(job, passed_match)
        for key in [
            "desire_score",
            "readiness_score",
            "exploration_score",
            "career_direction_summary",
            "career_direction_label",
        ]:
            self.assertEqual(conflicted[key], passed[key])
        self.assertNotEqual(
            conflicted["current_action_label"], passed["current_action_label"]
        )

    def test_unknown_preference_is_not_scored_as_neutral(self):
        job = load_json("fixtures/tencent_business_analysis_job_profile_expected.json")
        match = load_json("fixtures/tencent_business_analysis_match_expected.json")
        for alignment in match["task_alignments"]:
            alignment["preference_alignment"] = "untested"
        result = score_match(job, match)
        self.assertEqual(result["preference_coverage"], 0.0)
        self.assertIsNone(result["desire_score"])
        self.assertIsNone(result["career_direction_summary"])

    def test_actual_fde_pipeline_output_is_scoreable(self):
        result = score_match(
            load_json("eval_outputs/run-004/fde_normalized.json"),
            load_json("eval_outputs/match-run-003/fde_match_actual.json"),
        )
        self.assertEqual(result["preference_coverage"], 0.3)
        self.assertIsNone(result["career_direction_summary"])
        self.assertEqual(result["current_application_status"], "current_cycle_conflict")
        self.assertEqual(result["current_action_label"], "save_job_archetype")


if __name__ == "__main__":
    unittest.main()
