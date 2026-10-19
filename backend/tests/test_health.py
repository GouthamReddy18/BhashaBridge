import unittest
import os
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class HealthTests(unittest.TestCase):
    def test_health(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_readiness_reports_baseline_and_optional_model_separately(self):
        with patch.dict(os.environ, {"BHASHABRIDGE_TRANSLITERATION_ENABLED": "false"}):
            response = client.get("/ready")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["ready"]); self.assertEqual(payload["status"], "degraded")
        statuses = {module["name"]: module["status"] for module in payload["modules"]}
        self.assertEqual(statuses["api"], "available")
        self.assertEqual(statuses["language_identification"], "available")
        self.assertEqual(statuses["ambiguity_resolution"], "available")
        self.assertEqual(statuses["indic_lid_model"], "not_configured")
        self.assertEqual(statuses["transliteration"], "not_configured")
        self.assertEqual(statuses["translation"], "not_implemented")

    def test_optional_transliteration_does_not_initialize_engine_or_change_api_readiness(self):
        with patch.dict(os.environ, {"BHASHABRIDGE_TRANSLITERATION_ENABLED": "true"}):
            response = client.get("/ready")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        statuses = {module["name"]: module for module in payload["modules"]}
        self.assertEqual(statuses["api"]["status"], "available")
        self.assertEqual(statuses["transliteration"]["status"], "unavailable")
        self.assertIn("no verified offline engine is configured", statuses["transliteration"]["detail"])
        self.assertFalse(payload["ready"])  # Other unimplemented stages keep existing degraded status.

if __name__ == "__main__":
    unittest.main()
