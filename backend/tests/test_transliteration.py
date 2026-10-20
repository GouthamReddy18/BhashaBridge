import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.analysis import AnalyzeRequest, AnalyzedToken
from app.services.language_identification import RuleBasedTokenLanguageIdentifier
from app.services.pipeline import analyze
from app.services.tokenization import tokenize
from app.services.transliteration import transliterate_tokens


class FakeEngine:
    engine_id = "fake-local-test-engine"

    def __init__(self, result="\u0c2c\u0c3e\u0c17\u0c41\u0c28\u0c4d\u0c28\u0c3e\u0c35\u0c3e"):
        self.result = result
        self.calls = []

    def transliterate(self, text):
        self.calls.append(text)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class BrokenMetadataEngine(FakeEngine):
    @property
    def engine_id(self):
        raise RuntimeError("metadata failure")


def _annotated(text):
    tokens = tokenize(text)
    labels = RuleBasedTokenLanguageIdentifier().identify(tokens)
    return [AnalyzedToken(**token.model_dump(), language=label) for token, label in zip(tokens, labels, strict=True)]


class TransliterationTests(unittest.TestCase):
    def test_eligible_token_invokes_engine_and_records_genuine_candidate(self):
        engine = FakeEngine()
        records, status, _ = transliterate_tokens(_annotated("nenu"), enabled=True, engine=engine)
        self.assertEqual(engine.calls, ["nenu"])
        self.assertEqual(status, "available")
        self.assertEqual(records[0].candidate, engine.result)
        self.assertEqual(records[0].engine_id, engine.engine_id)
        self.assertEqual(records[0].status, "succeeded")

    def test_only_romanized_telugu_label_is_eligible_and_identity_is_preserved(self):
        annotated = _annotated("nenu hello \u0c28\u0c47\u0c28\u0c41 42 ! clg \u0928\u092e\u0938\u094d\u0924\u0947")
        engine = FakeEngine()
        records, _, _ = transliterate_tokens(annotated, enabled=True, engine=engine)
        self.assertEqual(engine.calls, ["nenu"])
        self.assertEqual([record.token_index for record in records], [token.index for token in annotated])
        self.assertEqual([(r.original_surface, r.start, r.end) for r in records], [(t.text, t.start, t.end) for t in annotated])
        self.assertEqual([r.status for r in records], ["succeeded", "skipped", "skipped", "skipped", "skipped", "skipped", "skipped"])
        self.assertEqual([r.detected_language for r in records], [t.language.label for t in annotated])

    def test_disabled_does_not_invoke_engine(self):
        engine = FakeEngine()
        records, status, _ = transliterate_tokens(_annotated("nenu"), enabled=False, engine=engine)
        self.assertEqual(engine.calls, [])
        self.assertEqual(records[0].status, "disabled")
        self.assertEqual(status, "not_configured")

    def test_enabled_without_verified_engine_is_explicitly_unavailable(self):
        records, status, detail = transliterate_tokens(_annotated("nenu"), enabled=True)
        self.assertEqual(status, "unavailable")
        self.assertIn("no verified offline engine is configured", detail)
        self.assertEqual(records[0].status, "unavailable")
        self.assertFalse(records[0].attempted)
        self.assertIsNone(records[0].candidate)

    def test_engine_exception_is_contained_at_analyze_endpoint(self):
        client = TestClient(app)
        engine = FakeEngine(RuntimeError("private detail"))
        original_analyze = analyze
        with patch("app.api.routes.analyze.analyze", side_effect=lambda request, **kwargs: original_analyze(
            request, transliteration_enabled=True, transliteration_engine=engine,
            translation_provider=kwargs.get("translation_provider")
        )):
            response = client.post("/api/v1/analyze", json={"text": "nenu"})
        self.assertEqual(response.status_code, 200)
        result = response.json()["transliterations"][0]
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "Engine raised RuntimeError.")
        self.assertNotIn("private detail", result["reason"])

    def test_engine_metadata_exception_is_contained_at_analyze_endpoint(self):
        client = TestClient(app)
        engine = BrokenMetadataEngine()
        original_analyze = analyze
        with patch("app.api.routes.analyze.analyze", side_effect=lambda request, **kwargs: original_analyze(
            request, transliteration_enabled=True, transliteration_engine=engine,
            translation_provider=kwargs.get("translation_provider")
        )):
            response = client.post("/api/v1/analyze", json={"text": "nenu"})
        self.assertEqual(response.status_code, 200)
        result = response.json()["transliterations"][0]
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["attempted"])
        self.assertNotIn("candidate", result)
        self.assertNotIn("engine_id", result)
        self.assertIn("metadata", result["reason"])

    def test_empty_and_non_telugu_engine_results_are_not_fabricated(self):
        telugu = "\u0c2c\u0c3e\u0c17\u0c41\u0c28\u0c4d\u0c28\u0c3e\u0c35\u0c3e"
        invalid_results = (None, 42, "", "   ", "hello", telugu + "\U0001f600",
                           telugu + "a", telugu + "!", telugu + "\u0928\u092e\u0938\u094d\u0924\u0947",
                           telugu + "\u0c66")
        for invalid in invalid_results:
            with self.subTest(invalid=invalid):
                records, _, _ = transliterate_tokens(_annotated("nenu"), enabled=True, engine=FakeEngine(invalid))
                self.assertEqual(records[0].status, "failed")
                self.assertIsNone(records[0].candidate)

    def test_valid_telugu_letters_and_combining_marks_are_accepted(self):
        candidate = "\u0c2c\u0c3e\u0c17\u0c41\u0c28\u0c4d\u0c28\u0c3e\u0c35\u0c3e"
        records, _, _ = transliterate_tokens(_annotated("nenu"), enabled=True, engine=FakeEngine(candidate))
        self.assertEqual(records[0].status, "succeeded")
        self.assertEqual(records[0].candidate, candidate)

    def test_default_configuration_disables_transliteration_and_preserves_api_fields(self):
        with patch.dict("os.environ", {"BHASHABRIDGE_TRANSLITERATION_ENABLED": "false"}):
            response = analyze(AnalyzeRequest(text="nenu"))
        self.assertEqual(response.original_text, "nenu")
        self.assertEqual(response.normalized_text, "nenu")
        self.assertEqual(response.tokens[0].language.label, "TELUGU_ROMANIZED")
        self.assertEqual(response.transliterations[0].status, "disabled")


if __name__ == "__main__":
    unittest.main()
