import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class ProjectReadinessApiTests(unittest.TestCase):
    def test_readiness_reports_real_draft_and_blocked_conditions(self):
        with patch.dict(os.environ, {"BHASHABRIDGE_GOOGLE_TRANSLATE_ENABLED": "false"}, clear=False):
            response = client.get("/api/v1/research/readiness")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["research_ready"])
        self.assertEqual(payload["dataset"]["name"], "illustrative_examples.jsonl")
        self.assertEqual(payload["dataset"]["structural_status"], "valid")
        self.assertEqual(payload["dataset"]["evaluation_status"], "not_ready")
        self.assertEqual(payload["dataset"]["records_examined"], 16)
        self.assertEqual(payload["dataset"]["structural_errors"], 0)
        self.assertEqual(payload["dataset"]["blocking_errors"], 144)
        self.assertEqual(payload["dataset"]["warnings"], 16)
        self.assertEqual(len(payload["dataset"]["blocker_categories"]), 6)
        self.assertTrue(any("reference translations" in item for item in payload["dataset"]["blocker_categories"]))
        self.assertTrue(any("intended meanings" in item for item in payload["dataset"]["blocker_categories"]))
        self.assertEqual(payload["provider"]["status"], "not_configured")
        conditions = {item["id"]: item for item in payload["conditions"]}
        self.assertEqual(conditions["direct_v1"]["status"], "blocked")
        self.assertEqual(conditions["normalized_v1"]["status"], "blocked")
        self.assertEqual(conditions["transliterated_v1"]["status"], "blocked")
        self.assertEqual(conditions["ambiguity_aware_v1"]["status"], "blocked")
        self.assertEqual(payload["evaluation_reports"]["status"], "not_catalogued")

    def test_readiness_endpoint_never_returns_paths_or_credentials(self):
        response = client.get("/api/v1/research/readiness")
        self.assertEqual(response.status_code, 200)
        serialized = response.text.casefold()
        self.assertNotIn("c:\\users\\", serialized)
        self.assertNotIn("api_key", serialized)


if __name__ == "__main__":
    unittest.main()
