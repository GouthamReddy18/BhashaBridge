"""In-memory paired direct/assisted translation orchestration."""
from app.schemas.analysis import AnalyzeRequest
from app.schemas.experiment import (
    ExperimentAnalysisTrace,
    ExperimentConfiguration,
    PairedExperimentResult,
    ProviderConfirmedMetadata,
    TranslationArmResult,
)
from app.services.assisted_input import build_assisted_input
from app.services.pipeline import analyze
from app.services.translation import (
    TranslationConfiguration,
    TranslationProvider,
    translate_text,
)


def run_paired_experiment(
    original_input: str,
    *,
    provider: TranslationProvider | None,
    configuration: ExperimentConfiguration | None = None,
    rules=None,
    allow_synthetic_test_fixtures: bool = False,
) -> PairedExperimentResult:
    """Run each arm in the configured order while retaining stable arm identity."""
    config = configuration or ExperimentConfiguration()
    provider_model = (
        getattr(provider, "requested_model", None)
        if callable(getattr(provider, "translate_configured", None))
        else None
    )
    if config.requested_model is None and isinstance(provider_model, str) and provider_model.strip():
        config = config.model_copy(update={"requested_model": provider_model})
    analysis = analyze(
        AnalyzeRequest(text=original_input, translate=False),
        translation_provider=None,
    )
    assisted = build_assisted_input(
        original_input=analysis.original_text,
        normalized_input=analysis.normalized_text,
        tokens=analysis.tokens,
        transliterations=analysis.transliterations,
        ambiguities=analysis.ambiguities,
        rules=rules,
        allow_synthetic_test_fixtures=allow_synthetic_test_fixtures,
    )

    intended_inputs = {
        "direct": original_input,
        "assisted": assisted.assisted_input,
    }
    configured_order = (
        ("direct", "assisted")
        if config.execution_order == "direct_first"
        else ("assisted", "direct")
    )
    outcomes = {}
    invocation_order = []
    for arm_name in configured_order:
        outcome = translate_text(
            intended_inputs[arm_name],
            requested=True,
            provider=provider,
            configuration=TranslationConfiguration(
                target_language=config.target_language,
                requested_model=config.requested_model,
                generation_settings=config.requested_generation_settings,
            ),
        )
        outcomes[arm_name] = outcome
        # input_text is set only after provider.translate was actually entered.
        if outcome.input_text is not None:
            invocation_order.append(arm_name)

    def build_arm(arm_name: str) -> TranslationArmResult:
        outcome = outcomes[arm_name]
        return TranslationArmResult(
            arm=arm_name,
            intended_input=intended_inputs[arm_name],
            provider_input=outcome.input_text,
            translation=outcome,
            provider_confirmed=ProviderConfirmedMetadata(
                provider_id=outcome.provider_id,
                model=outcome.provider_model,
            ),
        )

    return PairedExperimentResult(
        original_input=original_input,
        configuration=config,
        direct=build_arm("direct"),
        assisted=build_arm("assisted"),
        assisted_input=assisted,
        analysis=ExperimentAnalysisTrace(
            normalized_input=analysis.normalized_text,
            tokens=analysis.tokens,
            transliterations=analysis.transliterations,
            ambiguities=analysis.ambiguities,
        ),
        same_provider_instance_supplied=provider is not None,
        invocation_order=invocation_order,
        provider_configuration_forwarded=all(
            outcomes[arm].provider_configuration_forwarded is True
            for arm in ("direct", "assisted")
        ),
        provider_protocol_note=(
            "Both arms received the experiment settings through a configuration-aware provider."
            if all(outcomes[arm].provider_configuration_forwarded is True for arm in ("direct", "assisted"))
            else "At least one arm used a legacy text-only provider or did not reach configuration forwarding."
        ),
    )
