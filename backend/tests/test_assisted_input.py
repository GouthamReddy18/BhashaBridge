import unittest

from app.schemas.analysis import AnalyzeRequest
from app.schemas.experiment import AssistedInputResult
from pydantic import ValidationError
from app.schemas.experiment import TransformationRule
from app.services.assisted_input import build_assisted_input
from app.services.pipeline import analyze


def analyze_text(text, *, transliteration_enabled=None):
    return analyze(
        AnalyzeRequest(text=text, translate=False),
        transliteration_enabled=transliteration_enabled,
    )


def build(text, result=None, **kwargs):
    result = result or analyze_text(text)
    return build_assisted_input(
        original_input=text,
        normalized_input=result.normalized_text,
        tokens=result.tokens,
        transliterations=result.transliterations,
        ambiguities=result.ambiguities,
        **kwargs,
    )


def synthetic_rule(**overrides):
    values = {
        "rule_id": "test.synthetic.v1",
        "version": "1",
        "token_index": 0,
        "expected_surface": "nenu",
        "expected_language": "TELUGU_ROMANIZED",
        "replacement": "synthetic replacement",
        "provenance": "unit-test fixture",
        "evidence": "synthetic only",
        "evidence_status": "synthetic_fixture",
        "entity_review": "confirmed_non_entity",
    }
    values.update(overrides)
    return values


class AssistedInputTests(unittest.TestCase):
    def test_original_input_and_normalization_only_are_distinct(self):
        result = build("  nenu   college ")
        self.assertEqual(result.original_input, "  nenu   college ")
        self.assertEqual(result.normalized_input, "nenu college")
        self.assertEqual(result.assisted_input, result.normalized_input)
        self.assertTrue(result.normalization_only)
        self.assertFalse(result.meaningful_assistance)

    def test_unknown_telugu_script_numbers_punctuation_and_unicode_are_preserved(self):
        for text in ("clg", "తెలుగు", "42, nenu!", "😀 nenu"):
            self.assertEqual(build(text).assisted_input, text)

    def test_astral_offsets_remain_analysis_offsets(self):
        result = analyze_text("😀 nenu")
        assisted = build_assisted_input(
            original_input="😀 nenu",
            normalized_input=result.normalized_text,
            tokens=result.tokens,
            transliterations=result.transliterations,
            ambiguities=result.ambiguities,
        )
        self.assertEqual((result.tokens[1].start, result.tokens[1].end), (2, 6))
        self.assertEqual(assisted.assisted_input, "😀 nenu")
        self.assertEqual((result.tokens[1].start, result.tokens[1].end), (2, 6))

    def test_unavailable_transliteration_is_traced_and_never_used_as_replacement(self):
        analysis = analyze_text("nenu", transliteration_enabled=True)
        record = analysis.transliterations[0]
        self.assertEqual(record.status, "unavailable")
        result = build("nenu", analysis)
        self.assertEqual(result.assisted_input, "nenu")
        self.assertEqual(result.transformations, [])
        self.assertEqual(result.skipped_transformations[0].reason, "transliteration_unavailable_not_an_authorized_replacement")
        self.assertEqual(analysis.transliterations[0], record)

    def test_abstained_ambiguity_is_traced_without_candidate_replacement(self):
        analysis = analyze_text("bank")
        record = analysis.ambiguities[0]
        self.assertEqual(record.status, "abstained")
        self.assertIsNone(record.selected_candidate)
        result = build("bank", analysis)
        self.assertEqual(result.assisted_input, "bank")
        self.assertEqual(result.transformations, [])
        self.assertTrue(any(
            item.operation == "ambiguity" and item.reason == "abstained_no_candidate_selected"
            for item in result.skipped_transformations
        ))

    def test_illustrative_bank_candidate_is_never_replacement_text(self):
        analysis = analyze_text("river bank")
        self.assertEqual(analysis.ambiguities[0].status, "resolved")
        result = build("river bank", analysis)
        self.assertEqual(result.assisted_input, "river bank")
        self.assertEqual(result.transformations, [])

    def test_synthetic_rule_requires_explicit_test_opt_in(self):
        result = build("nenu", rules=[synthetic_rule()])
        self.assertEqual(result.assisted_input, "nenu")
        self.assertEqual(result.transformations, [])
        self.assertTrue(any(item.reason == "synthetic_fixture_test_opt_in_required" for item in result.skipped_transformations))

    def test_arbitrary_verified_provenance_cannot_enable_production_edit(self):
        rule = synthetic_rule(
            rule_id="caller.claim",
            evidence_status="verified",
            provenance="caller says verified",
            evidence="caller says reviewed",
        )
        result = build("nenu", rules=[rule])
        self.assertEqual(result.assisted_input, "nenu")
        self.assertEqual(result.transformations, [])
        self.assertTrue(any(item.reason == "production_transformations_disabled_no_trusted_registry" for item in result.skipped_transformations))

    def test_invalid_provenance_fails_closed(self):
        rule = synthetic_rule(provenance=" ")
        result = build("nenu", rules=[rule], allow_synthetic_test_fixtures=True)
        self.assertTrue(result.fallback)
        self.assertEqual(result.assisted_input, "nenu")

    def test_replacement_length_change_preserves_untouched_text(self):
        rule = synthetic_rule(replacement="much longer synthetic value")
        result = build("nenu college", rules=[rule], allow_synthetic_test_fixtures=True)
        self.assertEqual(result.assisted_input, "much longer synthetic value college")
        self.assertEqual(result.transformations[0].before, "nenu")

    def test_duplicate_and_overlapping_rule_spans_fail_atomically(self):
        duplicate_span = [
            synthetic_rule(rule_id="r1"),
            synthetic_rule(rule_id="r2"),
        ]
        result = build("nenu college", rules=duplicate_span, allow_synthetic_test_fixtures=True)
        self.assertTrue(result.fallback)
        self.assertEqual(result.assisted_input, "nenu college")
        self.assertEqual(result.transformations, [])

    def test_wrong_source_surface_fails_atomically(self):
        result = build(
            "nenu college",
            rules=[synthetic_rule(rule_id="r1"), synthetic_rule(
                rule_id="r2", token_index=1, expected_surface="wrong"
            )],
            allow_synthetic_test_fixtures=True,
        )
        self.assertTrue(result.fallback)
        self.assertEqual(result.assisted_input, "nenu college")
        self.assertEqual(result.transformations, [])

    def test_bad_analysis_spans_fall_back_without_partial_edit(self):
        analysis = analyze_text("nenu college")
        tokens = list(analysis.tokens)
        tokens[1] = tokens[1].model_copy(update={"start": 2, "end": 7})
        result = build_assisted_input(
            original_input="nenu college",
            normalized_input="nenu college",
            tokens=tokens,
            transliterations=analysis.transliterations,
            ambiguities=[],
            rules=[synthetic_rule()],
            allow_synthetic_test_fixtures=True,
        )
        self.assertTrue(result.fallback)
        self.assertEqual(result.assisted_input, "nenu college")
        self.assertEqual(result.transformations, [])

    def test_synthetic_transformation_trace_is_explicit(self):
        result = build("nenu", rules=[synthetic_rule()], allow_synthetic_test_fixtures=True)
        self.assertEqual(result.assisted_input, "synthetic replacement")
        self.assertEqual(len(result.transformations), 1)
        self.assertEqual(result.transformations[0].evidence_status, "synthetic_fixture")
        self.assertFalse(result.meaningful_assistance)
        self.assertFalse(result.normalization_only)
        self.assertFalse(result.assisted_input_equals_original)

    def test_model_rejects_meaningful_assistance_from_synthetic_only_trace(self):
        result = build("nenu", rules=[synthetic_rule()], allow_synthetic_test_fixtures=True)
        values = result.model_dump()
        self.assertFalse(values["meaningful_assistance"])
        values["meaningful_assistance"] = True
        with self.assertRaises(ValidationError):
            AssistedInputResult(**values)


    def test_direct_model_rejects_noncanonical_normalization_only(self):
        values = build(" nenu ").model_dump()
        values.update(
            normalized_input="invented",
            assisted_input="invented",
            assisted_input_equals_original=False,
            normalization_only=True,
        )
        with self.assertRaises(ValidationError):
            AssistedInputResult(**values)

    def test_direct_model_rejects_inconsistent_fallback_flags(self):
        valid = build("nenu")
        base = valid.model_dump()
        base.update(
            assisted_input="partial",
            assisted_input_equals_original=False,
            fallback=True,
            fallback_reason="safe fallback",
        )
        with self.assertRaises(ValidationError):
            AssistedInputResult(**base)

    def test_direct_model_rejects_fallback_with_transformations_or_assistance(self):
        base = build("nenu").model_dump()
        trace = {
            "rule_id": "fixture", "version": "1", "token_index": 0,
            "start": 0, "end": 4, "before": "nenu", "after": "changed",
            "provenance": "synthetic", "evidence": "test",
            "evidence_status": "synthetic_fixture",
        }
        contradictory = dict(base, fallback=True, fallback_reason="failed",
            transformations=[trace], meaningful_assistance=True)
        with self.assertRaises(ValidationError):
            AssistedInputResult(**contradictory)
        contradictory = dict(base, fallback=True, fallback_reason=" ",
            assisted_input="nenu")
        with self.assertRaises(ValidationError):
            AssistedInputResult(**contradictory)


if __name__ == "__main__":
    unittest.main()
