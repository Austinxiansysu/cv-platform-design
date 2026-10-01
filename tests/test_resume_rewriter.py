import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.backend.api import create_app
from src.backend.resume_rewriter import rewrite_resume_advice


ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


class FakeResponses:
    def __init__(self, output):
        self.output = output
        self.called_with = None

    def create(self, **kwargs):
        self.called_with = kwargs
        return SimpleNamespace(status="completed", output_text=json.dumps(self.output, ensure_ascii=False))


class ResumeRewriterTests(unittest.TestCase):
    def setUp(self):
        self.profile = fixture("profile_expected.json")
        self.profile["profile_meta"]["confirmation_status"] = "confirmed"
        self.job = fixture("fde_job_profile_expected.json")
        self.match = fixture("fde_match_expected.json")

    def _output(self, sentence):
        return {"rewrites": [{
            "experience_id": "P-X01",
            "suggested_sentence": sentence,
            "used_source_facts": ["企业官网项目", "使用AI工具参与需求到交付"],
            "explanation": "只调整了语序和连接词。",
        }]}

    def test_natural_wording_uses_only_selected_facts(self):
        responses = FakeResponses(self._output("在企业官网项目中，使用 AI 工具参与从需求到交付的过程。"))
        result = rewrite_resume_advice(self.profile, self.job, self.match, responses=responses)
        item = result["rewrites"][0]
        self.assertTrue(item["model_sentence_accepted"])
        self.assertTrue(item["requires_user_review"])
        self.assertIn("从需求到交付", item["suggested_sentence"])
        self.assertEqual(item["original_facts"]["evidence_ids"], ["P-E01"])
        sent = responses.called_with["input"]
        self.assertNotIn("中山大学", sent)
        self.assertNotIn("graduation_year", sent)
        self.assertEqual(responses.called_with["reasoning"], {"effort": "low"})
        self.assertFalse(responses.called_with["store"])

    def test_unsupported_claim_falls_back_to_strict_sentence(self):
        responses = FakeResponses(self._output("主导AI产品设计，提升转化率30%。"))
        result = rewrite_resume_advice(self.profile, self.job, self.match, responses=responses)
        item = result["rewrites"][0]
        self.assertFalse(item["model_sentence_accepted"])
        self.assertIsNotNone(item["rejection_reason"])
        self.assertNotIn("30%", item["suggested_sentence"])
        self.assertNotIn("主导", item["suggested_sentence"])

    def test_contact_details_in_fact_text_are_redacted_before_model_call(self):
        self.profile["experiences"][0]["user_actions"][0] += "，联系邮箱 test@example.com"
        responses = FakeResponses(self._output("在企业官网项目中，使用 AI 工具参与从需求到交付的过程。"))
        rewrite_resume_advice(self.profile, self.job, self.match, responses=responses)
        self.assertNotIn("test@example.com", responses.called_with["input"])

    def test_requirement_translation_is_preserved_across_role_emphases(self):
        experience = self.profile["experiences"][0]
        experience["title"] = "企业网站需求对接"
        experience["user_actions"] = [
            "对接企业真实网站需求，了解并整理需求后输出给AI",
        ]
        experience["deliverables"] = ["供AI实现的网站需求描述"]
        experience["tools"] = ["AI工具"]
        for focus, sentence in (
            ("AI产品：需求转译", "对接企业真实网站需求，整理为供AI实现的网站需求描述。"),
            ("商业分析：业务需求理解", "了解并整理企业真实网站需求，输出供AI实现的网站需求描述。"),
            ("企业数字化：业务与技术衔接", "将对接了解到的企业网站需求整理为供AI实现的描述。"),
        ):
            with self.subTest(focus=focus):
                self.match["user_facing_explanation"]["resume_focus_candidates"] = [focus]
                output = self._output(sentence)
                output["rewrites"][0]["used_source_facts"] = [
                    experience["title"], *experience["user_actions"], *experience["deliverables"],
                ]
                result = rewrite_resume_advice(
                    self.profile, self.job, self.match, responses=FakeResponses(output),
                )
                item = result["rewrites"][0]
                self.assertTrue(item["model_sentence_accepted"])
                self.assertEqual(item["job_focus"], [focus])
                self.assertEqual(item["original_facts"]["actions"], experience["user_actions"])
                self.assertTrue(item["requires_user_review"])

    def test_project_technology_does_not_imply_personal_skill(self):
        for sentence in (
            "使用WordPress和PHP完成企业官网项目。",
            "使用HTML、CSS和JavaScript完成企业官网项目。",
            "使用Trae完成企业官网项目。",
            "熟练使用AI工具完成企业官网项目。",
            "独立实现企业官网项目。",
        ):
            with self.subTest(sentence=sentence):
                result = rewrite_resume_advice(
                    self.profile, self.job, self.match,
                    responses=FakeResponses(self._output(sentence)),
                )
                item = result["rewrites"][0]
                self.assertFalse(item["model_sentence_accepted"])
                self.assertIsNotNone(item["rejection_reason"])

    def test_job_focus_cannot_supply_a_missing_personal_tool(self):
        self.match["user_facing_explanation"]["resume_focus_candidates"] = [
            "企业官网岗位需要WordPress与PHP",
        ]
        result = rewrite_resume_advice(
            self.profile, self.job, self.match,
            responses=FakeResponses(self._output("使用WordPress与PHP参与企业官网项目。")),
        )
        self.assertFalse(result["rewrites"][0]["model_sentence_accepted"])

    def test_api_requires_consent_and_does_not_save_rewrite(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "db.sqlite3"))
            self.assertEqual(client.post("/profiles", json=self.profile).status_code, 201)
            self.assertEqual(client.post("/jobs", json=self.job).status_code, 201)
            self.assertEqual(client.post("/matches", json=self.match).status_code, 201)
            path = f"/matches/{self.match['match_meta']['match_id']}/resume-rewrite"
            self.assertEqual(client.post(path, json={}).status_code, 422)
            with patch.dict(os.environ, {"CV_ASSISTANT_PROVIDER": "deepseek", "DEEPSEEK_API_KEY": ""}):
                self.assertEqual(client.post(path, json={
                    "consent_to_send_experience_facts": True,
                }).status_code, 503)

            expected = rewrite_resume_advice(
                self.profile, self.job, self.match,
                responses=FakeResponses(self._output("在企业官网项目中，使用 AI 工具参与从需求到交付的过程。")),
            )
            with patch("src.backend.api.rewrite_resume_advice", return_value=expected):
                response = client.post(path, json={"consent_to_send_experience_facts": True})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertFalse(response.json()["saved"])
            client.close()


if __name__ == "__main__":
    unittest.main()
