import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.backend.api import create_app


ROOT = Path(__file__).resolve().parents[1]


class ModelSettingsTests(unittest.TestCase):
    def test_key_stays_in_process_and_is_never_returned(self):
        job = json.loads(
            (ROOT / "fixtures" / "fde_job_profile_expected.json").read_text(encoding="utf-8")
        )
        secret = "sk-local-only-test-key-123456"
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "db.sqlite3"))
            with patch.dict(os.environ, {"CV_ASSISTANT_PROVIDER": "deepseek", "DEEPSEEK_API_KEY": ""}):
                self.assertFalse(client.get("/settings/model-status").json()["configured"])
                self.assertEqual(
                    client.post("/settings/model-key", json={"api_key": "short"}).status_code, 422
                )
                saved = client.post("/settings/model-key", json={"api_key": secret})
                self.assertEqual(saved.status_code, 200)
                self.assertNotIn(secret, saved.text)
                self.assertTrue(client.get("/settings/model-status").json()["configured"])
                self.assertNotIn(secret.encode(), (Path(directory) / "db.sqlite3").read_bytes())

                fake = SimpleNamespace(
                    responses=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(
                        status="completed", output_text=json.dumps(job, ensure_ascii=False)
                    ))
                )
                with patch("src.backend.model_gateway.OpenAI", return_value=fake) as factory:
                    analyzed = client.post("/jobs/analyze", json={
                        "jd_text": "飞书 FDE 实习生：调研客户需求，搭建 AI 工作流并提供培训支持。",
                        "source_type": "company_official",
                    })
                self.assertEqual(analyzed.status_code, 200, analyzed.text)
                self.assertEqual(factory.call_args.kwargs["api_key"], secret)
                self.assertFalse(analyzed.json()["saved"])
                self.assertEqual(client.get("/jobs").json(), [])

                cleared = client.delete("/settings/model-key")
                self.assertFalse(cleared.json()["configured"])
            client.close()

    def test_key_entry_rejects_nonlocal_client(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Path(directory) / "db.sqlite3")
            client = TestClient(app, client=("203.0.113.10", 12000))
            response = client.post("/settings/model-key", json={
                "api_key": "sk-local-only-test-key-123456",
            })
            self.assertEqual(response.status_code, 403)
            client.close()


if __name__ == "__main__":
    unittest.main()
