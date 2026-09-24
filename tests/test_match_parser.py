import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.backend.api import create_app
from src.backend.match_parser import analyze_match
from src.backend.model_gateway import ModelFailure


ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


class FakeResponses:
    def __init__(self, payload):
        self.payload = payload
        self.called_with = None

    def create(self, **kwargs):
        self.called_with = kwargs
        return SimpleNamespace(status="completed", output_text=json.dumps(self.payload, ensure_ascii=False))


class MatchParserTests(unittest.TestCase):
    def setUp(self):
        self.profile = fixture("profile_expected.json")
        self.job = fixture("fde_job_profile_expected.json")
        self.expected = fixture("fde_match_expected.json")

    def test_alignment_draft_uses_local_evidence_and_redacts_contact_in_request(self):
        profile = copy.deepcopy(self.profile)
        profile["evidence_registry"][0]["source_text"] += " test@example.com 13800138000"
        profile["evidence_registry"][0]["source_reference"] = "/Users/student/resume.docx"
        responses = FakeResponses(self.expected)
        alignment = analyze_match(profile, self.job, responses=responses)
        sent = responses.called_with["input"]
        self.assertNotIn("test@example.com", sent)
        self.assertNotIn("13800138000", sent)
        self.assertNotIn("/Users/student/resume.docx", sent)
        self.assertTrue(alignment["match_meta"]["match_id"].startswith("MATCH-LOCAL-"))
        self.assertEqual(alignment["profile_evidence_registry"][0]["source_text"],
                         profile["evidence_registry"][0]["source_text"])
        self.assertEqual(responses.called_with["model"], "deepseek-flash")

    def test_model_cannot_add_nonexistent_profile_evidence(self):
        result = copy.deepcopy(self.expected)
        result["task_alignments"][0]["preference_evidence_ids"] = ["made-up-id"]
        with self.assertRaises(ModelFailure):
            analyze_match(self.profile, self.job, responses=FakeResponses(result))

    def test_api_requires_consent_and_does_not_save_draft(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "db.sqlite3"))
            self.assertEqual(client.post("/profiles", json=self.profile).status_code, 201)
            self.assertEqual(client.post("/jobs", json=self.job).status_code, 201)
            request = {"profile_version": "profile-v1", "job_id": "JD-007"}
            self.assertEqual(client.post("/matches/analyze", json=request).status_code, 422)
            with patch.dict(os.environ, {"CV_ASSISTANT_PROVIDER": "deepseek", "DEEPSEEK_API_KEY": ""}):
                self.assertEqual(client.post("/matches/analyze", json={
                    **request, "consent_to_send_profile": True,
                }).status_code, 503)

            alignment = analyze_match(self.profile, self.job, responses=FakeResponses(self.expected))
            with patch("src.backend.api.analyze_match", return_value=alignment):
                response = client.post("/matches/analyze", json={
                    **request, "consent_to_send_profile": True,
                })
            self.assertEqual(response.status_code, 200, response.text)
            self.assertFalse(response.json()["saved"])
            self.assertIsNone(response.json()["score"]["career_direction_summary"])
            self.assertEqual(client.get(f"/matches/{alignment['match_meta']['match_id']}").status_code, 404)
            client.close()

    def test_unconfirmed_profile_cannot_be_matched(self):
        profile = copy.deepcopy(self.profile)
        profile["profile_meta"]["confirmation_status"] = "unconfirmed"
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "db.sqlite3"))
            self.assertEqual(client.post("/profiles", json=profile).status_code, 201)
            self.assertEqual(client.post("/jobs", json=self.job).status_code, 201)
            response = client.post("/matches/analyze", json={
                "profile_version": "profile-v1", "job_id": "JD-007",
                "consent_to_send_profile": True,
            })
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json()["detail"], "Confirm the profile before matching")
            client.close()


if __name__ == "__main__":
    unittest.main()
