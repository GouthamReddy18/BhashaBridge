import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.analysis import AnalyzeRequest
from app.services.pipeline import analyze
from app.services.tokenization import tokenize
from app.services.language_identification import RuleBasedTokenLanguageIdentifier

client = TestClient(app)


class LanguageIdentificationTests(unittest.TestCase):
    def test_telugu_script_detects_script_not_guaranteed_language(self):
        tokens = tokenize("\u0c28\u0c47\u0c28\u0c41")
        result = RuleBasedTokenLanguageIdentifier().identify(tokens)[0]
        self.assertEqual(result.label, "TELUGU_SCRIPT")
        self.assertIn("not guaranteed language", result.evidence)

    def test_known_english_lexicon_and_unknown_latin(self):
        tokens = tokenize("the clg")
        results = RuleBasedTokenLanguageIdentifier().identify(tokens)
        self.assertEqual([result.label for result in results], ["ENGLISH", "UNKNOWN"])

    def test_romanized_telugu_seed_and_unseen_uncertain_token(self):
        results = RuleBasedTokenLanguageIdentifier().identify(tokenize("nenu clg"))
        self.assertEqual([result.label for result in results], ["TELUGU_ROMANIZED", "UNKNOWN"])
        self.assertEqual(results[0].method, "romanized_telugu_seed_lexicon")
        self.assertEqual(results[1].method, "abstention")

    def test_punctuation_and_numbers_are_deterministic(self):
        results = RuleBasedTokenLanguageIdentifier().identify(tokenize("42!"))
        self.assertEqual([result.label for result in results], ["NUMBER", "PUNCTUATION"])
        self.assertIsNone(results[0].confidence)

    def test_mixed_text_classifies_without_sentence_position_rules(self):
        response = analyze(AnalyzeRequest(text="nenu college ki"))
        self.assertEqual([token.language.label for token in response.tokens], ["TELUGU_ROMANIZED", "ENGLISH", "TELUGU_ROMANIZED"])
        self.assertEqual([token.index for token in response.tokens], [0, 1, 2])

    def test_offsets_and_surface_tokens_preserved(self):
        text = "  nenu, college  "
        payload = client.post("/api/v1/analyze", json={"text": text}).json()
        self.assertEqual(payload["original_text"], text)
        self.assertEqual([(t["index"], t["text"], t["start"], t["end"]) for t in payload["tokens"]], [(0, "nenu", 0, 4), (1, ",", 4, 5), (2, "college", 6, 13)])
        self.assertEqual([t["language"]["label"] for t in payload["tokens"]], ["TELUGU_ROMANIZED", "PUNCTUATION", "ENGLISH"])

    def test_unavailable_model_uses_baseline_and_reports_status(self):
        with patch.dict(os.environ, {
            "BHASHABRIDGE_LID_PROVIDER": "indic_lid",
            "BHASHABRIDGE_INDICLID_FTN_PATH": "missing-ftn.bin",
            "BHASHABRIDGE_INDICLID_FTR_PATH": "missing-ftr.bin",
        }):
            response = client.post("/api/v1/analyze", json={"text": "nenu"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["tokens"][0]["language"]["label"], "TELUGU_ROMANIZED")
        statuses = {module["name"]: module["status"] for module in payload["modules"]}
        self.assertEqual(statuses["indic_lid_model"], "unavailable")

    def test_no_baseline_confidence_is_reported(self):
        result = RuleBasedTokenLanguageIdentifier().identify(tokenize("nenu"))[0]
        self.assertIsNone(result.confidence)
        response = client.post("/api/v1/analyze", json={"text": "nenu"}).json()
        self.assertNotIn("confidence", response["tokens"][0]["language"])


if __name__ == "__main__":
    unittest.main()
