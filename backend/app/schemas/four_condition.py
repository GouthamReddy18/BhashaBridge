"""Versioned contracts for the cumulative Phase 15 four-condition design."""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator, model_validator

from app.schemas.analysis import AmbiguityRecord, TranslationResult
from app.schemas.linguistic_resource import LinguisticResourceManifest
from app.schemas.evaluation import MetricConfiguration, MetricScores

ConditionId = Literal[
    "direct_v1", "normalized_v1", "transliterated_v1", "ambiguity_aware_v1",
]
ResourceKind = Literal["normalizer", "transliterator", "contextual_transformer"]
_SAFE_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,79}$")
_SECRET_MARKER = re.compile(r"(?:api.?key|secret|token|password|^sk-)", re.IGNORECASE)


class ContextualRuleMapping(BaseModel):
    """Bind a reviewed manifest rule to a specific resolved candidate decision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: StrictStr
    ambiguity_rule_id: StrictStr
    candidate_id: StrictStr


class ConditionResourceBinding(BaseModel):
    """Use a Phase 8 reviewed manifest for one explicit experimental operation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: ResourceKind
    manifest: LinguisticResourceManifest
    test_only: bool = False
    contextual_mappings: tuple[ContextualRuleMapping, ...] = ()

    @model_validator(mode="after")
    def validate_binding(self):
        rules = {rule.rule_id: rule for rule in self.manifest.rules}
        if any(
            not _SAFE_LABEL.fullmatch(getattr(self.manifest, field))
            or _SECRET_MARKER.search(getattr(self.manifest, field))
            for field in ("resource_id", "resource_version")
        ):
            raise ValueError("resource identifiers must be safe and must not contain secret-like values")
        for field in ("provenance",):
            if _SECRET_MARKER.search(getattr(self.manifest, field)):
                raise ValueError("resource metadata must not contain secret-like values")
        if self.kind == "contextual_transformer":
            if not self.contextual_mappings:
                raise ValueError("contextual resources require candidate mappings")
            mapping_ids = [mapping.rule_id for mapping in self.contextual_mappings]
            if len(mapping_ids) != len(set(mapping_ids)):
                raise ValueError("contextual mappings must reference unique rule IDs")
            for mapping in self.contextual_mappings:
                if mapping.rule_id not in rules:
                    raise ValueError("contextual mapping must reference a manifest rule")
        elif self.contextual_mappings:
            raise ValueError("contextual mappings are only valid for contextual resources")
        for rule in self.manifest.rules:
            if any(_SECRET_MARKER.search(value) for value in (
                rule.rule_id, rule.rule_version, rule.source_surface, rule.replacement,
                rule.applicability, rule.provenance, *rule.evidence_references,
            )):
                raise ValueError("resource rule metadata must not contain secret-like values")
            if rule.applicability != "exact_surface_and_language_match":
                raise ValueError("experimental rules require the supported exact-match applicability contract")
            if self.kind == "normalizer" and rule.source_language != rule.replacement_language:
                raise ValueError("normalization rules must preserve the token language")
            if self.kind == "transliterator" and (
                rule.source_language != "TELUGU_ROMANIZED"
                or rule.replacement_language != "TELUGU_SCRIPT"
            ):
                raise ValueError("transliteration rules must map Romanized Telugu to Telugu script")
        if self.kind == "transliterator" and not self.manifest.rules:
            raise ValueError("transliteration resources require at least one rule")
        return self

    @property
    def fingerprint(self) -> str:
        canonical = self.model_dump(mode="json")
        payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class FourConditionConfiguration(BaseModel):
    """Experiment-level provider settings and condition resources."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    experiment_version: Literal["four_condition.v1"] = "four_condition.v1"
    dataset_label: StrictStr
    split: Literal["train", "validation", "test"]
    target_language: Literal["en"] = "en"
    requested_model: StrictStr | None = None
    requested_generation_settings: dict[str, str | int | float | bool] = Field(default_factory=dict)
    execution_order: tuple[ConditionId, ...] = (
        "direct_v1", "normalized_v1", "transliterated_v1", "ambiguity_aware_v1",
    )
    resources: dict[ResourceKind, ConditionResourceBinding] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_configuration(self):
        required = ("direct_v1", "normalized_v1", "transliterated_v1", "ambiguity_aware_v1")
        if len(self.execution_order) != 4 or set(self.execution_order) != set(required):
            raise ValueError("execution_order must contain each of the four registered conditions exactly once")
        if not self.dataset_label.strip() or len(self.dataset_label) > 80:
            raise ValueError("dataset_label must be nonblank and at most 80 characters")
        if not _SAFE_LABEL.fullmatch(self.dataset_label) or _SECRET_MARKER.search(self.dataset_label):
            raise ValueError("dataset_label must be a safe short label without path or secret-like content")
        if self.requested_model is not None and _SECRET_MARKER.search(self.requested_model):
            raise ValueError("requested model metadata must not contain secret-like values")
        for key, value in self.requested_generation_settings.items():
            if _SECRET_MARKER.search(key) or (isinstance(value, str) and _SECRET_MARKER.search(value)):
                raise ValueError("generation settings must not contain secret-like values")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("generation settings must be finite")
        for key, binding in self.resources.items():
            if key != binding.kind:
                raise ValueError("resource key must match its declared kind")
        return self

    @property
    def fingerprint(self) -> str:
        canonical = self.model_dump(mode="json")
        payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ConditionTransformation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: ResourceKind
    resource_id: StrictStr
    resource_version: StrictStr
    rule_id: StrictStr
    rule_version: StrictStr
    token_index: int = Field(ge=0)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    before: StrictStr
    after: StrictStr
    evidence_references: tuple[StrictStr, ...]
    ambiguity_rule_id: StrictStr | None = None
    candidate_id: StrictStr | None = None
    context_evidence: StrictStr | None = None


class ConditionStageTrace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: ResourceKind
    input_text: StrictStr
    output_text: StrictStr
    status: Literal["completed", "blocked", "failed"]
    resource_id: StrictStr | None = None
    resource_version: StrictStr | None = None
    resource_fingerprint: StrictStr | None = None
    changed: bool
    applied_transformations: int = Field(ge=0)
    skipped_reasons: tuple[StrictStr, ...] = ()
    ambiguity_decisions: tuple[AmbiguityRecord, ...] = ()
    blocked_reason: StrictStr | None = None

    @model_validator(mode="after")
    def validate_trace(self):
        if self.status == "completed" and self.blocked_reason is not None:
            raise ValueError("completed stage cannot have a blocked reason")
        if self.status == "blocked" and (not self.blocked_reason or self.output_text != self.input_text):
            raise ValueError("blocked stage requires a reason and must preserve its input")
        if self.changed != (self.output_text != self.input_text):
            raise ValueError("stage changed flag must match its inputs")
        return self


class ConditionExecution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    condition_id: ConditionId
    condition_version: Literal["1.0"] = "1.0"
    dependencies: tuple[ConditionId, ...]
    status: Literal["completed", "blocked", "failed"]
    blocked_reason: StrictStr | None = None
    original_input: StrictStr
    intermediate_inputs: dict[str, StrictStr] = Field(default_factory=dict)
    intended_provider_input: StrictStr | None = None
    provider_input: StrictStr | None = None
    provider_call_attempted: bool
    translation: TranslationResult | None = None
    resource_references: tuple[str, ...] = ()
    transformations: tuple[ConditionTransformation, ...] = ()
    skipped_transformations: tuple[StrictStr, ...] = ()
    stages: tuple[ConditionStageTrace, ...] = ()
    intervention_applied: bool = False
    research_eligible: bool

    @model_validator(mode="after")
    def validate_execution(self):
        if self.status == "blocked":
            if not self.blocked_reason or self.intended_provider_input is not None or self.provider_call_attempted:
                raise ValueError("blocked condition must state why and cannot have an intended provider input or call")
            if self.translation is not None or self.provider_input is not None:
                raise ValueError("blocked condition cannot contain a translation outcome or provider input")
        elif self.blocked_reason is not None:
            raise ValueError("only blocked conditions may contain blocked_reason")
        if self.provider_call_attempted != (self.provider_input is not None):
            raise ValueError("provider call flag must agree with the recorded provider input")
        if self.provider_input is not None and self.provider_input != self.intended_provider_input:
            raise ValueError("actual provider input must equal the intended input")
        if self.translation is None and (self.provider_call_attempted or self.provider_input is not None):
            raise ValueError("provider metadata cannot claim an outcome or call when no translation outcome exists")
        if self.translation is not None and self.translation.input_text != self.provider_input:
            raise ValueError("provider input must agree with the translation invocation record")
        if self.translation is not None and any(
            value is not None and _SECRET_MARKER.search(value)
            for value in (self.translation.provider_id, self.translation.provider_model)
        ):
            raise ValueError("provider metadata must not contain secret-like values")
        if self.research_eligible and any(
            reference.startswith("test-only:") for reference in self.resource_references
        ):
            raise ValueError("test-only resources cannot be research-eligible")
        return self


class FourConditionExampleResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    original_input: StrictStr
    configuration_fingerprint: StrictStr
    conditions: tuple[ConditionExecution, ...]
    invocation_order: tuple[ConditionId, ...]
    test_fixture: bool = False

    @model_validator(mode="after")
    def validate_four_conditions(self):
        required = ("direct_v1", "normalized_v1", "transliterated_v1", "ambiguity_aware_v1")
        expected_dependencies = {
            "direct_v1": (), "normalized_v1": ("direct_v1",),
            "transliterated_v1": ("normalized_v1",),
            "ambiguity_aware_v1": ("transliterated_v1",),
        }
        ids = tuple(item.condition_id for item in self.conditions)
        if ids != required:
            raise ValueError("conditions must be serialized in the four-condition registry order")
        if len(set(self.invocation_order)) != len(self.invocation_order):
            raise ValueError("a condition can be invoked at most once")
        attempted = tuple(item.condition_id for item in self.conditions if item.provider_call_attempted)
        if set(self.invocation_order) != set(attempted) or len(self.invocation_order) != len(attempted):
            raise ValueError("invocation order must include each and only attempted provider call")
        if any(item.original_input != self.original_input for item in self.conditions):
            raise ValueError("all conditions must retain the exact original source input")
        for item in self.conditions:
            if item.dependencies != expected_dependencies[item.condition_id]:
                raise ValueError("condition dependencies contradict the registered cumulative design")
            if item.condition_id == "direct_v1" and item.intended_provider_input != self.original_input:
                raise ValueError("direct condition must use the exact original source")
            if item.status == "completed":
                expected_input = item.stages[-1].output_text if item.stages else self.original_input
                if item.intended_provider_input != expected_input:
                    raise ValueError("condition provider input must equal its final constructed stage")
                for left, right in zip(item.stages, item.stages[1:]):
                    if left.output_text != right.input_text:
                        raise ValueError("condition stage traces must be contiguous")
                if item.intervention_applied != bool(item.transformations):
                    raise ValueError("intervention flag must agree with applied transformations")
        if any(
            item.status == "completed" and item.intended_provider_input is not None
            and item.translation is None
            for item in self.conditions
        ):
            raise ValueError("every completed condition must record provider handling, including unavailable outcomes")
        if self.test_fixture and any(item.research_eligible for item in self.conditions):
            raise ValueError("test fixture results cannot be marked research-eligible")
        return self


class FourConditionArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    example_id: StrictStr
    split: Literal["train", "validation", "test"]
    configuration: FourConditionConfiguration
    result: FourConditionExampleResult

    @model_validator(mode="after")
    def validate_artifact(self):
        if not self.example_id.strip():
            raise ValueError("example_id must be nonblank")
        if self.split != self.configuration.split:
            raise ValueError("artifact split must match experiment configuration")
        if self.result.configuration_fingerprint != self.configuration.fingerprint:
            raise ValueError("configuration fingerprint does not match serialized configuration")
        if self.result.original_input != self.result.conditions[0].original_input:
            raise ValueError("artifact source must match condition source")
        if any(item.research_eligible for item in self.result.conditions) and self.result.test_fixture:
            raise ValueError("test artifacts cannot contain research-eligible conditions")
        return self


class ConditionEvaluationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome_counts: dict[str, int]
    available_example_ids: tuple[StrictStr, ...]
    available_examples: int = Field(ge=0)
    excluded_example_ids: tuple[StrictStr, ...]
    scores: MetricScores
    blocked_conditions: int = Field(ge=0)
    research_eligible: bool


class ConditionComparison(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    comparison_id: StrictStr
    numerator_condition: ConditionId
    denominator_condition: ConditionId
    matched_example_ids: tuple[StrictStr, ...]
    matched_examples: int = Field(ge=0)
    excluded_example_ids: tuple[StrictStr, ...]
    numerator_scores: MetricScores
    denominator_scores: MetricScores
    numerator_minus_denominator: MetricScores

    @field_validator("numerator_scores", "denominator_scores", "numerator_minus_denominator")
    @classmethod
    def finite_metrics(cls, value):
        for score in (value.bleu, value.chrf):
            if score is not None and not math.isfinite(score):
                raise ValueError("metric scores must be finite")
        return value


class FourConditionEvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    report_status: Literal["evaluated", "no_metric_population", "not_evaluated", "test_fixture_only"]
    dataset_label: StrictStr
    split: Literal["train", "validation", "test"]
    experiment_version: Literal["four_condition.v1"]
    configuration_fingerprint: StrictStr | None = None
    metric_configuration: MetricConfiguration
    records_discovered: int = Field(ge=0)
    eligible_records: int = Field(ge=0)
    eligible_example_ids: tuple[StrictStr, ...]
    excluded_records: int = Field(ge=0)
    orphan_artifacts: int = Field(ge=0)
    readiness_diagnostic_counts: dict[str, int]
    variants: dict[ConditionId, ConditionEvaluationSummary]
    comparisons: tuple[ConditionComparison, ...]
    human_semantic_preservation: Literal["pending"] = "pending"
    limitations: tuple[StrictStr, ...]

    @model_validator(mode="after")
    def validate_safe_report_metadata(self):
        if not _SAFE_LABEL.fullmatch(self.dataset_label) or _SECRET_MARKER.search(self.dataset_label):
            raise ValueError("report dataset label must be a safe short label")
        return self
