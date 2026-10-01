import copy
import json
import unittest
from pathlib import Path

from src.backend.match_normalization import normalize_match_alignment
from src.matching.scoring import score_match


ROOT = Path(__file__).resolve().parents[1]


class MatchNormalizationTests(unittest.TestCase):
    def setUp(self):
        read = lambda name: json.loads((ROOT / "fixtures" / name).read_text())
        self.profile = read("profile_expected.json")
        self.job = read("fde_job_profile_expected.json")
        self.match = read("fde_match_expected.json")
        self.target = self.match["task_alignments"][2]
        self.job["task_clusters"][2]["cluster_name"] = "案例SOP与演示模板沉淀"
        self.target["preference_alignment"] = "negative"
        self.target["preference_evidence_ids"] = ["P-E05"]

    def test_archive_dislike_cannot_create_a_documentation_dislike_score(self):
        normalize_match_alignment(self.profile, self.job, self.match)
        self.assertEqual(self.target["preference_alignment"], "untested")
        self.assertEqual(self.target["preference_evidence_ids"], [])
        result = score_match(self.job, self.match)
        self.assertEqual(result["preference_coverage"], 0.3)
        self.assertIsNone(result["career_direction_summary"])
        self.assertTrue(self.match["match_meta"]["warnings"])
        before = copy.deepcopy(self.match)
        self.assertEqual(normalize_match_alignment(self.profile, self.job, self.match), [])
        self.assertEqual(self.match, before)

    def test_direct_sop_dislike_is_not_erased(self):
        self.profile["evidence_registry"][-1]["source_text"] = "不喜欢合规档案整理，也明确不喜欢编写方案SOP"
        normalize_match_alignment(self.profile, self.job, self.match)
        self.assertEqual(self.target["preference_alignment"], "negative")

    def test_actual_archive_task_keeps_its_dislike(self):
        self.job["task_clusters"][2]["cluster_name"] = "合规档案归档"
        normalize_match_alignment(self.profile, self.job, self.match)
        self.assertEqual(self.target["preference_alignment"], "negative")

    def test_missing_evidence_is_not_hidden_by_correction(self):
        self.target["preference_evidence_ids"] = ["nonexistent"]
        normalize_match_alignment(self.profile, self.job, self.match)
        self.assertEqual(self.target["preference_evidence_ids"], ["nonexistent"])

    def test_unproven_capability_is_an_evidence_gap(self):
        item = self.match["capability_alignments"][0]
        item.update(status="not_demonstrated", gap_type="confirmed_gap")
        normalize_match_alignment(self.profile, self.job, self.match)
        self.assertEqual(item["gap_type"], "evidence_gap")

    def test_unknown_condition_moves_to_information_without_erasing_real_conflicts(self):
        self.match["gap_summary"]["structural_feasibility_gaps"] = [
            "工作地点未知，无法判断", "实习最短6个月，用户不能满足，工作模式可能可协商",
        ]
        normalize_match_alignment(self.profile, self.job, self.match)
        self.assertIn("工作地点未知，无法判断", self.match["gap_summary"]["information_gaps"])
        self.assertEqual(len(self.match["gap_summary"]["structural_feasibility_gaps"]), 1)


if __name__ == "__main__":
    unittest.main()
