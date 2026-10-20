import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.analysis import AnalyzeRequest, AnalyzedToken, TransliterationResult
from app.services.ambiguity_resolution import resolve_ambiguities
from app.services.language_identification import RuleBasedTokenLanguageIdentifier
from app.services.pipeline import analyze
from app.services.tokenization import tokenize


def _tokens(text):
    raw = tokenize(text)
    labels = RuleBasedTokenLanguageIdentifier().identify(raw)
    return [
        AnalyzedToken(**token.model_dump(), language=label)
        for token, label in zip(raw, labels, strict=True)
    ]


class FakeFailingEngine:
    engine_id = "fake-failing-engine"

    def transliterate(self, text):
        raise RuntimeError("private engine detail")


class AmbiguityResolutionTests(unittest.TestCase):
    def test_illustrative_fixture_resolves_with_matching_context(self):
        record = analyze(AnalyzeRequest(text="account bank")).ambiguities[0]
        self.assertEqual(record.rule_id, "fixture.english_bank_immediate_context.v1")
        self.assertEqual(record.status, "resolved")
        self.assertEqual(record.selected_candidate, "financial_institution")
        self.assertIn("account", record.evidence)
        self.assertEqual(record.candidates[0].source, "illustrative_project_fixture:english_bank_polysemy")

    def test_illustrative_fixture_abstains_without_context(self):
        record = analyze(AnalyzeRequest(text="bank")).ambiguities[0]
        self.assertEqual(record.status, "abstained")
        self.assertIsNone(record.selected_candidate)
        self.assertIn("insufficient", record.evidence)

    def test_conflicting_context_abstains(self):
        record = analyze(AnalyzeRequest(text="account bank river")).ambiguities[0]
        self.assertEqual(record.status, "abstained")
        self.assertIsNone(record.selected_candidate)
        self.assertIn("Conflicting", record.evidence)

    def test_unknown_latin_token_is_not_automatically_ambiguous(self):
        response = analyze(AnalyzeRequest(text="clg"))
        self.assertEqual(response.tokens[0].language.label, "UNKNOWN")
        self.assertEqual(response.ambiguities, [])

    def test_ordinary_unambiguous_token_has_no_record(self):
        self.assertEqual(analyze(AnalyzeRequest(text="hello")).ambiguities, [])

    def test_other_language_labels_are_preserved(self):
        text = "bank \u0c28\u0c47\u0c28\u0c41 nenu"
        tokens = _tokens(text)
        before = [token.language.label for token in tokens]
        records = resolve_ambiguities(normalized_text=text, tokens=tokens, transliterations=[])
        self.assertEqual([token.language.label for token in tokens], before)
        self.assertEqual(before, ["ENGLISH", "TELUGU_SCRIPT", "TELUGU_ROMANIZED"])
        self.assertEqual([record.token_index for record in records], [0])

    def test_unknown_river_anchor_is_used_without_relabeling(self):
        response = analyze(AnalyzeRequest(text="river bank"))
        self.assertEqual(response.tokens[0].language.label, "UNKNOWN")
        self.assertEqual(response.tokens[1].language.label, "ENGLISH")
        self.assertEqual(response.ambiguities[0].status, "resolved")
        self.assertEqual(response.ambiguities[0].selected_candidate, "river_edge")
        self.assertEqual(response.tokens[0].language.label, "UNKNOWN")

    def test_arbitrary_unknown_neighbor_does_not_supply_evidence(self):
        response = analyze(AnalyzeRequest(text="clg bank"))
        self.assertEqual(response.tokens[0].language.label, "UNKNOWN")
        self.assertEqual(response.ambiguities[0].status, "abstained")
        self.assertIsNone(response.ambiguities[0].selected_candidate)

    def test_number_is_not_a_context_anchor(self):
        response = analyze(AnalyzeRequest(text="42 bank"))
        self.assertEqual(
            [(token.text, token.start, token.end) for token in response.tokens],
            [("42", 0, 2), ("bank", 3, 7)],
        )
        self.assertEqual(response.tokens[0].language.label, "NUMBER")
        self.assertEqual(response.ambiguities[0].status, "abstained")

    def test_punctuation_blocks_a_non_immediate_anchor(self):
        response = analyze(AnalyzeRequest(text="river , bank"))
        self.assertEqual(
            [(token.text, token.start, token.end) for token in response.tokens],
            [("river", 0, 5), (",", 6, 7), ("bank", 8, 12)],
        )
        self.assertEqual(response.ambiguities[0].status, "abstained")
        self.assertIsNone(response.ambiguities[0].selected_candidate)

    def test_substring_does_not_create_an_ambiguity_target(self):
        response = analyze(AnalyzeRequest(text="riverbank"))
        self.assertEqual(response.tokens[0].language.label, "UNKNOWN")
        self.assertEqual(response.ambiguities, [])

    def test_configured_anchor_matching_is_casefolded(self):
        response = analyze(AnalyzeRequest(text="RiVeR bank"))
        self.assertEqual(response.tokens[0].language.label, "UNKNOWN")
        self.assertEqual(response.ambiguities[0].status, "resolved")
        self.assertEqual(response.ambiguities[0].selected_candidate, "river_edge")

    def _record_data(self, status, selected_candidate):
        return {
            "token_index": 1,
            "surface": "bank",
            "start": 8,
            "end": 12,
            "status": status,
            "candidates": [
                {
                    "candidate_id": "financial_institution",
                    "description": "illustrative fixture candidate",
                    "source": "illustrative_project_fixture:english_bank_polysemy",
                },
                {
                    "candidate_id": "river_edge",
                    "description": "illustrative fixture candidate",
                    "source": "illustrative_project_fixture:english_bank_polysemy",
                },
            ],
            "selected_candidate": selected_candidate,
            "rule_id": "fixture.english_bank_immediate_context.v1",
            "evidence": "fixture test evidence",
        }

    def test_schema_accepts_consistent_resolved_and_abstained_records(self):
        from app.schemas.analysis import AmbiguityRecord
        resolved = AmbiguityRecord.model_validate(
            self._record_data("resolved", "financial_institution")
        )
        abstained = AmbiguityRecord.model_validate(self._record_data("abstained", None))
        self.assertEqual(resolved.selected_candidate, "financial_institution")
        self.assertIsNone(abstained.selected_candidate)

    def test_schema_rejects_resolved_record_without_selection(self):
        from pydantic import ValidationError
        from app.schemas.analysis import AmbiguityRecord
        with self.assertRaises(ValidationError):
            AmbiguityRecord.model_validate(self._record_data("resolved", None))

    def test_schema_rejects_selection_not_in_candidates(self):
        from pydantic import ValidationError
        from app.schemas.analysis import AmbiguityRecord
        with self.assertRaises(ValidationError):
            AmbiguityRecord.model_validate(
                self._record_data("resolved", "unconfigured_candidate")
            )

    def test_schema_rejects_abstained_record_with_selection(self):
        from pydantic import ValidationError
        from app.schemas.analysis import AmbiguityRecord
        with self.assertRaises(ValidationError):
            AmbiguityRecord.model_validate(
                self._record_data("abstained", "river_edge")
            )

    def test_numbers_and_punctuation_do_not_match_fixture(self):
        self.assertEqual(analyze(AnalyzeRequest(text="42 !")).ambiguities, [])

    def test_disabled_transliteration_does_not_invoke_injected_engine(self):
        class CountingEngine:
            engine_id = "counting"
            def __init__(self):
                self.calls = []
            def transliterate(self, text):
                self.calls.append(text)
                return None

        engine = CountingEngine()
        response = analyze(
            AnalyzeRequest(text="account bank nenu"),
            transliteration_enabled=False,
            transliteration_engine=engine,
        )
        self.assertEqual(engine.calls, [])
        self.assertEqual(response.ambiguities[0].status, "resolved")

    def test_failed_or_unavailable_target_transliteration_does_not_fabricate_evidence(self):
        text = "account bank"
        tokens = _tokens(text)
        for status in ("failed", "unavailable"):
            result = TransliterationResult(
                token_index=1, original_surface="bank", start=8, end=12,
                detected_language="ENGLISH", attempted=(status == "failed"),
                status=status, reason="synthetic status fixture",
            )
            records = resolve_ambiguities(
                normalized_text=text, tokens=tokens, transliterations=[result]
            )
            self.assertEqual(records[0].status, "resolved")
            self.assertEqual(records[0].selected_candidate, "financial_institution")
            self.assertNotIn("transliteration", records[0].evidence.casefold())

    def test_repeated_surfaces_keep_indices_and_offsets(self):
        text = "account bank bank"
        response = analyze(AnalyzeRequest(text=text))
        self.assertEqual([record.token_index for record in response.ambiguities], [1, 2])
        for record in response.ambiguities:
            token = response.tokens[record.token_index]
            self.assertEqual((record.surface, record.start, record.end), (token.text, token.start, token.end))
            self.assertEqual(text[record.start:record.end], record.surface)

    def test_astral_unicode_before_candidate_preserves_python_offsets(self):
        text = "\U0001f600 account bank"
        response = analyze(AnalyzeRequest(text=text))
        record = response.ambiguities[0]
        self.assertEqual(record.token_index, 2)
        self.assertEqual((record.start, record.end), (text.index("bank"), text.index("bank") + len("bank")))
        self.assertEqual(response.normalized_text[record.start:record.end], record.surface)

    def test_api_compatibility_and_engine_exception(self):
        client = TestClient(app)
        original_analyze = analyze
        with patch("app.api.routes.analyze.analyze", side_effect=lambda request, **kwargs: original_analyze(
            request, transliteration_enabled=True, transliteration_engine=FakeFailingEngine(),
            translation_provider=kwargs.get("translation_provider")
        )):
            response = client.post("/api/v1/analyze", json={"text": "nenu account bank"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        for field in ("original_text", "normalized_text", "tokens", "transliterations", "modules", "ambiguities"):
            self.assertIn(field, payload)
        self.assertEqual(payload["transliterations"][0]["status"], "failed")
        self.assertEqual(payload["ambiguities"][0]["status"], "resolved")

    def test_determinism_and_empty_results(self):
        first = analyze(AnalyzeRequest(text="account bank")).ambiguities
        second = analyze(AnalyzeRequest(text="account bank")).ambiguities
        self.assertEqual(first, second)
        self.assertEqual(analyze(AnalyzeRequest(text="hello")).ambiguities, [])
        self.assertEqual(analyze(AnalyzeRequest(text=" \thello  ")).ambiguities, [])


if __name__ == "__main__":
    unittest.main()
