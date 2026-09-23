import copy
import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.backend.api import create_app


ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


class BackendApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.directory.name) / "local.sqlite3"
        self.client = TestClient(create_app(self.db_path))
        self.profile = fixture("profile_expected.json")
        self.job = fixture("fde_job_profile_expected.json")
        self.match = fixture("fde_match_expected.json")

    def tearDown(self):
        self.client.close()
        self.directory.cleanup()

    def _seed_profile_job(self):
        self.assertEqual(self.client.post("/profiles", json=self.profile).status_code, 201)
        self.assertEqual(self.client.post("/jobs", json=self.job).status_code, 201)

    def test_full_local_flow_persists_and_recomputes_score(self):
        self._seed_profile_job()
        response = self.client.post("/matches", json=self.match)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["score"]["current_action_label"], "save_job_archetype")
        self.assertIsNone(response.json()["score"]["career_direction_summary"])

        application = self.client.post("/applications", json={
            "company": "字节跳动", "role": "飞书 FDE", "job_id": "JD-007",
            "match_id": self.match["match_meta"]["match_id"], "status": "saved",
        })
        self.assertEqual(application.status_code, 201, application.text)
        application_id = application.json()["application_id"]
        updated = self.client.patch(f"/applications/{application_id}", json={
            "status": "interview", "interviewed": True, "notes": "已确认面试",
        })
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertTrue(updated.json()["interviewed"])

        reopened = TestClient(create_app(self.db_path))
        self.assertEqual(reopened.get("/profiles/profile-v1").json(), self.profile)
        self.assertEqual(reopened.get("/jobs/JD-007").json(), self.job)
        self.assertEqual(reopened.get(f"/applications/{application_id}").json()["status"], "interview")
        reopened.close()
        self.assertEqual(self.client.delete(f"/applications/{application_id}").status_code, 204)
        self.assertEqual(self.client.get(f"/applications/{application_id}").status_code, 404)

    def test_invalid_payload_and_missing_references_are_rejected(self):
        invalid = copy.deepcopy(self.profile)
        invalid["profile_meta"]["confirmation_status"] = "invented"
        self.assertEqual(self.client.post("/profiles", json=invalid).status_code, 422)
        self.assertEqual(self.client.post("/matches", json=self.match).status_code, 404)
        self._seed_profile_job()

        incomplete = copy.deepcopy(self.match)
        incomplete["task_alignments"] = incomplete["task_alignments"][:-1]
        response = self.client.post("/matches", json=incomplete)
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["detail"][0]["type"], "task_alignment_mismatch")

        self.assertEqual(self.client.post("/jobs", json=self.job).status_code, 409)
        self.assertEqual(self.client.get("/jobs/not-found").status_code, 404)


if __name__ == "__main__":
    unittest.main()
