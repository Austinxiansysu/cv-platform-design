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

    def test_known_duration_conflict_beats_hypothetical_remote_or_split_exception(self):
        self.job["basic_conditions"]["duration_months"]["minimum"] = 6
        self.profile["availability_constraints"]["duration_months_max"] = 3
        self.match["current_application_eligibility"]["status"] = "pending"
        self.match["current_application_eligibility"]["unknown_conditions"] = ["是否允许远程或分段未知"]
        normalize_match_alignment(self.profile, self.job, self.match)
        eligibility = self.match["current_application_eligibility"]
        self.assertEqual(eligibility["status"], "current_cycle_conflict")
        self.assertIn("至少6个月", eligibility["explanation"])
        self.assertEqual(eligibility["unknown_conditions"], ["是否允许远程或分段未知"])
        self.assertEqual(score_match(self.job, self.match)["current_action_label"], "save_job_archetype")

    def test_unknown_duration_or_sufficient_window_does_not_create_a_conflict(self):
        for minimum in (None, 2, 3):
            with self.subTest(minimum=minimum):
                match = copy.deepcopy(self.match)
                match["current_application_eligibility"]["status"] = "pending"
                self.job["basic_conditions"]["duration_months"]["minimum"] = minimum
                normalize_match_alignment(self.profile, self.job, match)
                self.assertEqual(match["current_application_eligibility"]["status"], "pending")

    def test_conditional_job_requirement_is_information_not_a_confirmed_conflict(self):
        self.match["gap_summary"]["structural_feasibility_gaps"] = [
            "用户学期内不可实习，若岗位要求学期内到岗则存在结构性冲突",
            "岗位明确要求至少6个月，用户不能满足；如果岗位可远程仍待核实",
        ]
        normalize_match_alignment(self.profile, self.job, self.match)
        self.assertEqual(len(self.match["gap_summary"]["structural_feasibility_gaps"]), 1)
        self.assertIn("明确要求", self.match["gap_summary"]["structural_feasibility_gaps"][0])

    def test_missing_evidence_summary_does_not_become_an_ability_shortfall(self):
        self.match["gap_summary"]["capability_gaps"] = ["未提供证据：英文熟练", "用户已确认不会SQL"]
        normalize_match_alignment(self.profile, self.job, self.match)
        self.assertEqual(self.match["gap_summary"]["capability_gaps"], ["用户已确认不会SQL"])
        self.assertIn("未提供证据：英文熟练", self.match["gap_summary"]["evidence_gaps"])


if __name__ == "__main__":
    unittest.main()
