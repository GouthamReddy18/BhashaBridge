import unittest

from pydantic import ValidationError

from app.schemas.analysis import TranslationResult
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


class AssistedOnlyFailureProvider(FakeProvider):
    def translate(self, request):
        self.calls.append(request)
        if request.text == "nenu":
            raise RuntimeError("private assisted failure")
        return ProviderTranslation("direct output")


class ProviderIdFailureProvider:
    @property
    def provider_id(self):
        raise RuntimeError("private provider metadata")

    def translate(self, request):
        raise AssertionError("translate must not run after provider ID failure")


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

    def test_default_order_is_direct_first_and_records_attempts(self):
        provider = FakeProvider()
        result = run_paired_experiment(" nenu ", provider=provider)
        self.assertEqual(result.configuration.execution_order, "direct_first")
        self.assertEqual(result.invocation_order, ["direct", "assisted"])
        self.assertEqual([call.text for call in provider.calls], [" nenu ", "nenu"])
        self.assertEqual(result.direct.arm, "direct")
        self.assertEqual(result.assisted.arm, "assisted")

    def test_assisted_first_order_keeps_stable_arm_identity_and_inputs(self):
        provider = FakeProvider()
        configuration = ExperimentConfiguration(execution_order="assisted_first")
        result = run_paired_experiment("  nenu  ", provider=provider, configuration=configuration)
        self.assertEqual(result.invocation_order, ["assisted", "direct"])
        self.assertEqual([call.text for call in provider.calls], ["nenu", "  nenu  "])
        self.assertEqual(result.direct.provider_input, "  nenu  ")
        self.assertEqual(result.assisted.provider_input, "nenu")
        self.assertEqual(result.direct.arm, "direct")
        self.assertEqual(result.assisted.arm, "assisted")

    def test_invalid_execution_order_is_rejected(self):
        with self.assertRaises(ValidationError):
            ExperimentConfiguration(execution_order="random")

    def test_invocation_order_must_match_actual_recorded_calls(self):
        result = run_paired_experiment("nenu", provider=FakeProvider()).model_dump()
        bad = {**result, "invocation_order": ["assisted", "direct"]}
        with self.assertRaises(ValidationError):
            PairedExperimentResult(**bad)
        invented = {**result, "invocation_order": ["direct"]}
        with self.assertRaises(ValidationError):
            PairedExperimentResult(**invented)

    def test_arm_schema_rejects_provider_inputs_inconsistent_with_invocation(self):
        with self.assertRaises(ValidationError):
            TranslationArmResult(
                arm="direct",
                intended_input="source",
                provider_input=None,
                translation=TranslationResult(
                    status="failed", provider_id="fixture.fake",
                    error_code="provider_error",
                ),
                provider_confirmed={"provider_id": "fixture.fake"},
            )
        with self.assertRaises(ValidationError):
            TranslationArmResult(
                arm="direct",
                intended_input="source",
                provider_input="source",
                translation=TranslationResult(
                    status="failed", error_code="provider_metadata_error",
                ),
                provider_confirmed={"provider_id": None},
            )

    def test_unavailable_provider_records_no_attempts(self):
        result = run_paired_experiment("nenu", provider=None)
        self.assertEqual(result.invocation_order, [])
        self.assertIsNone(result.direct.provider_input)
        self.assertIsNone(result.assisted.provider_input)

    def test_provider_id_failure_records_no_provider_invocation(self):
        result = run_paired_experiment("nenu", provider=ProviderIdFailureProvider())
        self.assertEqual(result.invocation_order, [])
        self.assertEqual(result.direct.translation.error_code, "provider_metadata_error")
        self.assertIsNone(result.direct.provider_input)
        self.assertEqual(result.assisted.translation.error_code, "provider_metadata_error")

    def test_assisted_failure_preserves_direct_result_in_assisted_first_order(self):
        provider = AssistedOnlyFailureProvider()
        config = ExperimentConfiguration(execution_order="assisted_first")
        result = run_paired_experiment("  nenu  ", provider=provider, configuration=config)
        self.assertEqual(result.invocation_order, ["assisted", "direct"])
        self.assertEqual(result.assisted.translation.status, "failed")
        self.assertEqual(result.direct.translation.status, "success")
        self.assertEqual(result.direct.translation.translated_text, "direct output")

    def test_both_failed_attempts_are_recorded_in_execution_order(self):
        result = run_paired_experiment(
            "nenu", provider=FakeProvider(fail=True),
            configuration=ExperimentConfiguration(execution_order="assisted_first"),
        )
        self.assertEqual(result.invocation_order, ["assisted", "direct"])
        self.assertEqual(result.assisted.translation.status, "failed")
        self.assertEqual(result.direct.translation.status, "failed")
        self.assertEqual(result.assisted.translation.error_code, "provider_error")
        self.assertEqual(result.direct.translation.error_code, "provider_error")

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
        self.assertEqual(no_provider.invocation_order, [])
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
        self.assertEqual(result.invocation_order, ["direct", "assisted"])
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

    def test_provider_model_confirmation_must_match_provider_response(self):
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
