import unittest

from pydantic import ValidationError

from app.schemas.experiment import (
    ExperimentConfiguration,
    PairedExperimentResult,
    TranslationArmResult,
)
from app.services.experiment import run_paired_experiment
from app.services.translation import ProviderTranslation, TranslationInput


class FakeProvider:
    provider_id = "fixture.fake"

    def __init__(self, fail=False, empty=False):
        self.calls = []
        self.fail = fail
        self.empty = empty

    def translate(self, request):
        self.calls.append(request)
        if self.fail:
            raise RuntimeError("private provider detail")
        return ProviderTranslation("" if self.empty else "fixture output")


class FirstCallFailsProvider(FakeProvider):
    def translate(self, request):
        self.calls.append(request)
        if len(self.calls) == 1:
            raise RuntimeError("first call failure")
        return ProviderTranslation("second arm output")


class ExperimentTests(unittest.TestCase):
    def test_direct_receives_exact_original_unicode_and_whitespace(self):
        text = "  😀 తెలుగు nenu "
        provider = FakeProvider()
        result = run_paired_experiment(text, provider=provider)
        self.assertEqual(provider.calls[0], TranslationInput(text=text))
        self.assertEqual(result.direct.intended_input, text)
        self.assertEqual(result.direct.provider_input, text)

    def test_assisted_arm_uses_exact_builder_output(self):
        provider = FakeProvider()
        result = run_paired_experiment("  nenu   college ", provider=provider)
        self.assertEqual(provider.calls[1].text, result.assisted_input.assisted_input)
        self.assertEqual(result.assisted.intended_input, "nenu college")
        self.assertEqual(result.assisted.provider_input, "nenu college")

    def test_requested_configuration_is_not_reported_as_confirmed_or_forwarded(self):
        configuration = ExperimentConfiguration(
            target_language="en",
            requested_model="future-model",
            requested_generation_settings={"temperature": 0},
        )
        result = run_paired_experiment("nenu", provider=FakeProvider(), configuration=configuration)
        self.assertEqual(result.configuration, configuration)
        self.assertFalse(result.provider_configuration_forwarded)
        self.assertIsNone(result.direct.provider_confirmed.target_language)
        self.assertIsNone(result.direct.provider_confirmed.model)

    def test_provider_free_and_failed_outcomes_remain_valid(self):
        no_provider = run_paired_experiment("nenu", provider=None)
        self.assertEqual(no_provider.direct.translation.status, "unavailable")
        self.assertEqual(no_provider.direct.intended_input, "nenu")
        self.assertIsNone(no_provider.direct.provider_input)
        failed = run_paired_experiment("nenu", provider=FakeProvider(fail=True))
        self.assertEqual(failed.direct.translation.status, "failed")
        invalid = run_paired_experiment("nenu", provider=FakeProvider(empty=True))
        self.assertEqual(invalid.assisted.translation.status, "failed")

    def test_first_arm_failure_does_not_prevent_second_arm_invocation(self):
        provider = FirstCallFailsProvider()
        result = run_paired_experiment("nenu", provider=provider)
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(result.direct.translation.error_code, "provider_error")
        self.assertEqual(result.assisted.translation.status, "success")
        self.assertEqual(result.assisted.translation.input_text, result.assisted.provider_input)

    def test_provider_inputs_match_actual_calls_and_no_score_is_created(self):
        provider = FakeProvider()
        result = run_paired_experiment(" nenu ", provider=provider)
        self.assertEqual(result.direct.provider_input, provider.calls[0].text)
        self.assertEqual(result.assisted.provider_input, provider.calls[1].text)
        self.assertEqual(result.direct.intended_input, provider.calls[0].text)
        self.assertEqual(result.assisted.intended_input, provider.calls[1].text)
        self.assertFalse(hasattr(result, "score"))
        self.assertFalse(hasattr(result, "reference_translation"))

    def test_synthetic_rule_is_traced_in_assisted_arm_only(self):
        rule = dict(
            rule_id="test.synthetic", version="1", token_index=0,
            expected_surface="nenu", expected_language="TELUGU_ROMANIZED",
            replacement="fixture", provenance="synthetic test", evidence="test",
            evidence_status="synthetic_fixture", entity_review="confirmed_non_entity",
        )
        provider = FakeProvider()
        result = run_paired_experiment(
            "nenu", provider=provider, rules=[rule],
            allow_synthetic_test_fixtures=True,
        )
        self.assertEqual([call.text for call in provider.calls], ["nenu", "fixture"])
        self.assertFalse(result.assisted_input.meaningful_assistance)

    def test_disabled_translation_arm_is_rejected(self):
        result = run_paired_experiment("nenu", provider=FakeProvider())
        arm = result.direct.model_dump()
        arm["translation"] = {"status": "disabled"}
        with self.assertRaises(ValidationError):
            TranslationArmResult(**arm)

    def test_contradictory_pair_records_are_rejected(self):
        result = run_paired_experiment("nenu", provider=FakeProvider()).model_dump()
        wrong_direct = {**result, "direct": {**result["direct"], "intended_input": "other"}}
        with self.assertRaises(ValidationError):
            PairedExperimentResult(**wrong_direct)
        wrong_normalization = {**result, "analysis": {**result["analysis"], "normalized_input": "other"}}
        with self.assertRaises(ValidationError):
            PairedExperimentResult(**wrong_normalization)
        false_provider_state = {**result, "same_provider_instance_supplied": False}
        with self.assertRaises(ValidationError):
            PairedExperimentResult(**false_provider_state)

    def test_text_only_protocol_rejects_provider_confirmed_target_or_model(self):
        result = run_paired_experiment("nenu", provider=FakeProvider()).model_dump()
        bad = {**result, "direct": {**result["direct"], "provider_confirmed": {
            "provider_id": "fixture.fake", "target_language": "en", "model": "fake"
        }}}
        with self.assertRaises(ValidationError):
            PairedExperimentResult(**bad)

    def test_bank_fixture_does_not_become_a_semantic_substitution(self):
        result = run_paired_experiment("river bank", provider=FakeProvider())
        self.assertEqual(result.assisted.provider_input, "river bank")
        self.assertFalse(result.assisted_input.meaningful_assistance)


if __name__ == "__main__":
    unittest.main()
