"""Typed in-memory records for the controlled Phase 6B experiment."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, model_validator

from app.services.preprocessing import normalize_whitespace

from app.schemas.analysis import (
    AmbiguityRecord,
    AnalyzedToken,
    TranslationResult,
    TransliterationResult,
)


class TransformationRule(BaseModel):
    """Caller-declared rule metadata; it is not proof of linguistic verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: StrictStr
    version: StrictStr
    token_index: int = Field(ge=0)
    expected_surface: StrictStr
    expected_language: Literal["TELUGU_ROMANIZED", "ENGLISH"]
    replacement: StrictStr
    provenance: StrictStr
    evidence: StrictStr
    evidence_status: Literal["verified", "synthetic_fixture"]
    entity_review: Literal["confirmed_non_entity"]

    @model_validator(mode="after")
    def validate_nonblank_metadata(self):
        for name in (
            "rule_id", "version", "expected_surface", "replacement",
            "provenance", "evidence",
        ):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must be nonblank")
        return self


class TransformationRecord(BaseModel):
    rule_id: str
    version: str
    token_index: int = Field(ge=0)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    before: str
    after: str
    provenance: str
    evidence: str
    evidence_status: Literal["synthetic_fixture"]

    @model_validator(mode="after")
    def validate_applied_edit(self):
        if self.end <= self.start:
            raise ValueError("transformation span must be nonempty")
        if not all(value.strip() for value in (
            self.rule_id, self.version, self.before, self.after,
            self.provenance, self.evidence,
        )):
            raise ValueError("transformation trace strings must be nonblank")
        if self.before == self.after:
            raise ValueError("applied transformation must change the token")
        return self


class SkippedTransformation(BaseModel):
    token_index: int | None = None
    operation: str
    reason: str
    rule_id: str | None = None


class AssistedInputResult(BaseModel):
    original_input: str
    normalized_input: str
    assisted_input: str
    transformations: list[TransformationRecord] = Field(default_factory=list)
    skipped_transformations: list[SkippedTransformation] = Field(default_factory=list)
    meaningful_assistance: bool
    assisted_input_equals_original: bool
    normalization_only: bool
    fallback: bool = False
    fallback_reason: str | None = None

    @model_validator(mode="after")
    def validate_result_invariants(self):
        if normalize_whitespace(self.original_input) != self.normalized_input:
            raise ValueError("normalized_input must use project whitespace normalization")
        if self.assisted_input_equals_original != (self.assisted_input == self.original_input):
            raise ValueError("assisted_input_equals_original must match the input values")

        if self.fallback:
            if self.assisted_input != self.original_input:
                raise ValueError("fallback must preserve the exact original input")
            if self.transformations:
                raise ValueError("fallback cannot contain applied transformations")
            if self.meaningful_assistance:
                raise ValueError("fallback cannot claim meaningful assistance")
            if self.normalization_only:
                raise ValueError("fallback cannot be normalization-only")
            if self.fallback_reason is None or not self.fallback_reason.strip():
                raise ValueError("fallback requires a nonblank reason")
        elif self.fallback_reason is not None:
            raise ValueError("fallback_reason is only valid when fallback is true")

        if self.meaningful_assistance:
            if not self.transformations:
                raise ValueError("meaningful_assistance requires an applied transformation")
            if any(
                item.evidence_status == "synthetic_fixture"
                for item in self.transformations
            ):
                raise ValueError(
                    "synthetic transformations cannot establish meaningful linguistic assistance"
                )
        if self.normalization_only and self.meaningful_assistance:
            raise ValueError("normalization-only cannot claim meaningful assistance")
        expected_normalization_only = (
            not self.fallback
            and not self.transformations
            and self.assisted_input == self.normalized_input
            and self.normalized_input != self.original_input
        )
        if self.normalization_only != expected_normalization_only:
            raise ValueError("normalization_only must reflect whitespace-only changes")
        return self


class ExperimentConfiguration(BaseModel):
    """Requested configuration, distinct from provider-confirmed metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target_language: Literal["en"] = "en"
    execution_order: Literal["direct_first", "assisted_first"] = "direct_first"
    requested_model: str | None = None
    requested_generation_settings: dict[str, str | int | float | bool] = Field(default_factory=dict)


class ProviderConfirmedMetadata(BaseModel):
    """Provider-confirmed identity and any model returned by the provider."""

    model_config = ConfigDict(extra="forbid")

    provider_id: str | None = None
    target_language: None = None
    model: str | None = None


class ExperimentAnalysisTrace(BaseModel):
    normalized_input: str
    tokens: list[AnalyzedToken]
    transliterations: list[TransliterationResult]
    ambiguities: list[AmbiguityRecord]


class TranslationArmResult(BaseModel):
    arm: Literal["direct", "assisted"]
    intended_input: str
    provider_input: str | None = None
    translation: TranslationResult
    provider_confirmed: ProviderConfirmedMetadata

    @model_validator(mode="after")
    def validate_arm_result(self):
        if self.translation.status == "disabled":
            raise ValueError("experiment arms represent requested translation")
        if self.translation.input_text != self.provider_input:
            raise ValueError("provider_input must match the actual recorded provider input")
        if (
            self.translation.error_code == "provider_metadata_error"
            and self.provider_input is not None
        ):
            raise ValueError("provider metadata failure occurs before provider invocation")
        if self.translation.error_code in {
            "provider_error", "invalid_provider_output", "provider_timeout",
            "provider_auth_error", "provider_quota_error", "provider_response_error",
        } and self.provider_input is None:
            raise ValueError("provider-call failures must retain the attempted input")
        if self.provider_input is not None and self.provider_input != self.intended_input:
            raise ValueError("actual provider input must match intended arm input")
        if self.translation.provider_id != self.provider_confirmed.provider_id:
            raise ValueError("confirmed provider ID must match the translation result")
        if self.translation.provider_model != self.provider_confirmed.model:
            raise ValueError("confirmed model must match provider response metadata")
        if self.provider_confirmed.target_language is not None:
            raise ValueError("provider target language is not confirmed by the response")
        if self.translation.error_code == "provider_configuration_error" and self.provider_input is not None:
            raise ValueError("provider configuration errors occur before provider invocation")
        if self.translation.error_code in {
            "provider_error", "invalid_provider_output", "provider_timeout",
            "provider_auth_error", "provider_quota_error", "provider_request_error",
            "provider_response_error",
        } and self.provider_input is None:
            raise ValueError("provider-call failures must retain the attempted input")
        return self


class PairedExperimentResult(BaseModel):
    original_input: str
    configuration: ExperimentConfiguration
    direct: TranslationArmResult
    assisted: TranslationArmResult
    assisted_input: AssistedInputResult
    analysis: ExperimentAnalysisTrace
    same_provider_instance_supplied: bool
    invocation_order: list[Literal["direct", "assisted"]] = Field(default_factory=list)
    provider_configuration_forwarded: bool = False
    provider_protocol_note: str = (
        "Legacy providers receive text only; configuration-aware providers receive explicit experiment settings."
    )

    @model_validator(mode="after")
    def validate_pair(self):
        if self.assisted_input.original_input != self.original_input:
            raise ValueError("assisted input must refer to the paired original input")
        if self.direct.arm != "direct" or self.assisted.arm != "assisted":
            raise ValueError("paired result must contain direct and assisted arms")
        if self.direct.intended_input != self.original_input:
            raise ValueError("direct arm must intend the exact original input")
        if self.assisted.intended_input != self.assisted_input.assisted_input:
            raise ValueError("assisted arm must intend the constructed input")
        if self.analysis.normalized_input != self.assisted_input.normalized_input:
            raise ValueError("analysis and assisted-input normalization must match")
        if len(self.invocation_order) != len(set(self.invocation_order)):
            raise ValueError("each experiment arm can be invoked at most once")
        attempted = [
            name for name in ("direct", "assisted")
            if getattr(self, name).translation.input_text is not None
        ]
        configured_order = (
            ["direct", "assisted"]
            if self.configuration.execution_order == "direct_first"
            else ["assisted", "direct"]
        )
        expected_invocations = [name for name in configured_order if name in attempted]
        if self.invocation_order != expected_invocations:
            raise ValueError(
                "invocation_order must match configured order for attempted arms"
            )
        if not self.same_provider_instance_supplied:
            for arm in (self.direct, self.assisted):
                if arm.translation.status != "unavailable" or arm.translation.error_code != "provider_not_configured":
                    raise ValueError("provider-free experiment arms must be unavailable")
        else:
            for arm in (self.direct, self.assisted):
                if arm.translation.status == "unavailable":
                    raise ValueError("configured provider cannot be reported as unconfigured")
        forwarded_by_arms = all(
            getattr(self, arm).translation.provider_configuration_forwarded is True
            for arm in ("direct", "assisted")
        )
        if self.provider_configuration_forwarded != forwarded_by_arms:
            raise ValueError("provider_configuration_forwarded must reflect both arm outcomes")
        return self
