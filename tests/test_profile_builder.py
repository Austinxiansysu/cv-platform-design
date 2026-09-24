import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.backend.api import create_app
from src.backend.profile_builder import analyze_profile


ROOT = Path(__file__).resolve().parents[1]


class FakeResponses:
    def __init__(self, payload):
        self.payload = payload
        self.called_with = None

    def create(self, **kwargs):
        self.called_with = kwargs
        return SimpleNamespace(status="completed", output_text=json.dumps(self.payload, ensure_ascii=False))


class ProfileBuilderTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads(
            (ROOT / "fixtures" / "profile_expected.json").read_text(encoding="utf-8")
        )
        self.resume = "金融专业本科生，参与过企业官网项目。邮箱 test@example.com，手机 13800138000。"
        self.preferences = "喜欢行业研究、数据分析和实际解决问题，只考虑寒暑假在广州或深圳实习。"

    def test_draft_redacts_contact_details_and_requires_confirmation(self):
        responses = FakeResponses(self.profile)
        draft = analyze_profile(
            self.resume, self.preferences, {"school": "中山大学"}, responses=responses
        )
        sent = responses.called_with["input"]
        self.assertNotIn("test@example.com", sent)
        self.assertNotIn("13800138000", sent)
        self.assertTrue(draft["profile_meta"]["profile_version"].startswith("PROFILE-LOCAL-"))
        self.assertEqual(draft["profile_meta"]["confirmation_status"], "unconfirmed")
        self.assertEqual(responses.called_with["model"], "deepseek-flash")

    def test_api_opt_in_and_draft_not_saved(self):
        request = {
            "resume_text": self.resume,
            "preferences_text": self.preferences,
            "basic_info": {"school": "中山大学"},
        }
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "db.sqlite3"))
            self.assertEqual(client.post("/profiles/analyze", json=request).status_code, 422)
            with patch.dict(os.environ, {"CV_ASSISTANT_PROVIDER": "deepseek", "DEEPSEEK_API_KEY": ""}):
                self.assertEqual(client.post("/profiles/analyze", json={
                    **request, "consent_to_send_resume": True,
                }).status_code, 503)

            draft = analyze_profile(self.resume, self.preferences, {}, responses=FakeResponses(self.profile))
            with patch("src.backend.api.analyze_profile", return_value=draft):
                response = client.post("/profiles/analyze", json={
                    **request, "consent_to_send_resume": True,
                })
            self.assertEqual(response.status_code, 200, response.text)
            self.assertFalse(response.json()["saved"])
            self.assertEqual(client.get(f"/profiles/{draft['profile_meta']['profile_version']}").status_code, 404)
            client.close()


if __name__ == "__main__":
    unittest.main()
