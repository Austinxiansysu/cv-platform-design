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
from src.backend.job_parser import ParserFailure, analyze_job_text


ROOT = Path(__file__).resolve().parents[1]


class FakeResponses:
    def __init__(self, body, status="completed"):
        self.body = body
        self.status = status
        self.called_with = None

    def create(self, **kwargs):
        self.called_with = kwargs
        return SimpleNamespace(status=self.status, output_text=self.body)


class JobParserTests(unittest.TestCase):
    def setUp(self):
        self.job = json.loads(
            (ROOT / "fixtures" / "fde_job_profile_expected.json").read_text(encoding="utf-8")
        )
        self.jd = "飞书 FDE 实习生：调研企业客户的业务难题，搭建飞书 AI 工作流 Demo，并培训合作伙伴。"

    def test_structured_draft_has_server_metadata_and_is_not_saved(self):
        responses = FakeResponses(json.dumps(self.job, ensure_ascii=False))
        draft = analyze_job_text(
            self.jd, "school_channel", "local_group_screenshot", responses=responses
        )
        self.assertTrue(draft["job_meta"]["job_id"].startswith("JD-LOCAL-"))
        self.assertEqual(draft["job_meta"]["source_type"], "school_channel")
        self.assertEqual(draft["job_meta"]["source_reference"], "local_group_screenshot")
        self.assertEqual(draft["job_meta"]["posting_status"], "unknown")
        self.assertEqual(draft["job_meta"]["source_reliability"], "low")
        self.assertFalse(responses.called_with["store"])
        self.assertEqual(responses.called_with["text"]["format"]["type"], "json_schema")
        self.assertEqual(responses.called_with["model"], "deepseek-flash")
        self.assertEqual(responses.called_with["reasoning"], {"effort": "low"})
        self.assertNotIn("strict", responses.called_with["text"]["format"])

        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "db.sqlite3"))
            with patch("src.backend.api.analyze_job_text", return_value=draft):
                response = client.post("/jobs/analyze", json={"jd_text": self.jd})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertFalse(response.json()["saved"])
            self.assertEqual(client.get("/jobs").json(), [])
            client.close()

    def test_missing_key_and_invalid_model_output_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "db.sqlite3"))
            with patch.dict(os.environ, {"CV_ASSISTANT_PROVIDER": "deepseek", "DEEPSEEK_API_KEY": ""}):
                response = client.post("/jobs/analyze", json={"jd_text": self.jd})
            self.assertEqual(response.status_code, 503)
            self.assertEqual(client.get("/jobs").json(), [])
            client.close()

        bad = FakeResponses("{bad json}")
        with self.assertRaises(ParserFailure):
            analyze_job_text(self.jd, "unknown", "user_paste", responses=bad)

    def test_explicit_openai_provider_retains_strict_format(self):
        responses = FakeResponses(json.dumps(self.job, ensure_ascii=False))
        with patch.dict(os.environ, {"CV_ASSISTANT_PROVIDER": "openai"}):
            analyze_job_text(self.jd, "unknown", "user_paste", responses=responses)
        self.assertEqual(responses.called_with["model"], "gpt-5.6-luna")
        self.assertTrue(responses.called_with["text"]["format"]["strict"])

    def test_deepseek_provider_uses_its_own_key_and_endpoint(self):
        responses = FakeResponses(json.dumps(self.job, ensure_ascii=False))
        with patch.dict(os.environ, {
            "CV_ASSISTANT_PROVIDER": "deepseek",
            "DEEPSEEK_API_KEY": "local-test-key",
        }):
            with patch("src.backend.model_gateway.OpenAI") as client:
                client.return_value.responses = responses
                analyze_job_text(self.jd, "unknown", "user_paste")
        self.assertEqual(client.call_args.kwargs["api_key"], "local-test-key")
        self.assertEqual(client.call_args.kwargs["base_url"], "https://api.deepseek.com")
        self.assertEqual(responses.called_with["model"], "deepseek-flash")

    def test_model_semantic_mislabels_are_normalized_before_return(self):
        model_job = copy.deepcopy(self.job)
        model_job["capability_requirements"][0]["claim_type"] = "inferred"
        model_job["capability_requirements"][0]["requirement_strength"] = "must"
        model_job["basic_conditions"]["other_application_conditions"].append({
            "condition_name": "学历", "normalized_value": "本科",
            "requirement_strength": "must", "gate_type": "hard_gate",
            "evidence_id": "J07-E01",
        })
        draft = analyze_job_text(
            self.jd, "company_official", "user_paste",
            responses=FakeResponses(json.dumps(model_job, ensure_ascii=False)),
        )
        self.assertEqual(draft["capability_requirements"][0]["requirement_strength"], "uncertain")
        self.assertEqual(draft["basic_conditions"]["other_application_conditions"], [])
        self.assertTrue(any("系统归一化" in text for text in draft["job_uncertainties"]["warnings"]))


if __name__ == "__main__":
    unittest.main()
