import copy
import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.backend.api import create_app
from src.matching.resume_advice import build_resume_advice


ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


class ResumeAdviceTests(unittest.TestCase):
    def setUp(self):
        self.profile = fixture("profile_expected.json")
        self.job = fixture("fde_job_profile_expected.json")
        self.match = fixture("fde_match_expected.json")

    def test_unconfirmed_details_do_not_become_resume_bullets(self):
        advice = build_resume_advice(self.profile, self.job, self.match)
        self.assertEqual(advice["suggestions"], [])
        self.assertEqual(len(advice["needs_more_information"]), 3)

    def test_confirmed_facts_generate_only_source_bound_sentence(self):
        profile = copy.deepcopy(self.profile)
        profile["profile_meta"]["confirmation_status"] = "confirmed"
        advice = build_resume_advice(profile, self.job, self.match)
        self.assertEqual(len(advice["suggestions"]), 1)
        item = advice["suggestions"][0]
        self.assertEqual(item["experience_id"], "P-X01")
        self.assertIn("使用AI工具参与需求到交付", item["suggested_sentence"])
        self.assertIn("企业官网", item["suggested_sentence"])
        self.assertNotIn("AI产品经理经验", item["suggested_sentence"])
        self.assertIn("AI产品经理经验", item["prohibited_claims"])
        self.assertTrue(item["requires_user_review"])
        self.assertEqual(len(advice["needs_more_information"]), 2)

    def test_api_returns_advice_for_saved_match(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "db.sqlite3"))
            self.assertEqual(client.post("/profiles", json=self.profile).status_code, 201)
            self.assertEqual(client.post("/jobs", json=self.job).status_code, 201)
            self.assertEqual(client.post("/matches", json=self.match).status_code, 201)
            response = client.get(f"/matches/{self.match['match_meta']['match_id']}/resume-advice")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["match_id"], self.match["match_meta"]["match_id"])
            self.assertEqual(response.json()["suggestions"], [])
            client.close()

    def test_one_eligible_experience_keeps_paraphrased_job_focus(self):
        profile = copy.deepcopy(self.profile)
        profile["profile_meta"]["confirmation_status"] = "confirmed"
        match = copy.deepcopy(self.match)
        match["user_facing_explanation"]["resume_focus_candidates"] = [
            "网站需求理解与交付过程",
        ]
        advice = build_resume_advice(profile, self.job, match)
        self.assertEqual(advice["suggestions"][0]["job_focus"], ["网站需求理解与交付过程"])


if __name__ == "__main__":
    unittest.main()
