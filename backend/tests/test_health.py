import unittest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class HealthTests(unittest.TestCase):
    def test_health(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_readiness_does_not_claim_nlp_available(self):
        response = client.get("/ready")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["ready"]); self.assertEqual(payload["status"], "degraded")
        statuses = {module["name"]: module["status"] for module in payload["modules"]}
        self.assertEqual(statuses["api"], "available")
        self.assertEqual(statuses["translation"], "not_implemented")
        self.assertEqual(statuses["language_identification"], "not_implemented")

if __name__ == "__main__":
    unittest.main()
