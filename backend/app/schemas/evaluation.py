"""Versioned input and report contracts for offline paired evaluation."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator

from app.schemas.experiment import PairedExperimentResult


class PairedEvaluationArtifact(BaseModel):
    """One JSONL row joining an annotation ID to an existing paired result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    example_id: StrictStr
    split: Literal["train", "validation", "test"] | None = None
    result: PairedExperimentResult

    @field_validator("example_id")
    @classmethod
    def require_nonblank_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("example_id must be nonblank")
        return value


class MetricConfiguration(BaseModel):
    """Fixed in-project metric settings; unsupported variants are rejected."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    implementation: Literal["bhashabridge.metrics"] = "bhashabridge.metrics"
    version: Literal["1.0.0"] = "1.0.0"
    normalization: Literal["Unicode NFC; collapse whitespace"] = "Unicode NFC; collapse whitespace"
    case_sensitive: Literal[True] = True
    bleu_tokenization: Literal["whitespace; punctuation remains attached"] = (
        "whitespace; punctuation remains attached"
    )
    bleu_order: Literal[4] = 4
    bleu_smoothing: Literal["exponential zero-count smoothing"] = "exponential zero-count smoothing"
    bleu_effective_order: Literal[True] = True
    chrf_char_order: Literal[6] = 6
    chrf_word_order: Literal[0] = 0
    chrf_beta: Literal[2.0] = 2.0
    chrf_spaces: Literal[False] = False


class MetricScores(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    bleu: float | None = None
    chrf: float | None = None


class MetricPopulation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    denominator: str
    examples: int = Field(ge=0)
    scores: MetricScores


class ArmEvaluationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome_counts: dict[str, int]
    failure_code_counts: dict[str, int]
    confirmed_provider_ids: list[str]
    confirmed_provider_models: list[str] = Field(default_factory=list)
    available_output_example_ids: list[StrictStr] = Field(default_factory=list)
    attempted_invocations: int = Field(ge=0)
    pre_invocation_failures: int = Field(ge=0)
    available_output_population: MetricPopulation
    matched_pair_population: MetricPopulation


class ExclusionCount(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reason: str
    examples: int = Field(ge=0)


class PerExampleComparison(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    example_id: str
    bleu_direct: float
    bleu_assisted: float
    bleu_assisted_minus_direct: float
    chrf_direct: float
    chrf_assisted: float
    chrf_assisted_minus_direct: float


class EvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    evaluation_status: Literal["evaluated", "not_evaluated", "no_metric_population"]
    dataset_label: str
    split: Literal["train", "validation", "test"]
    metric_configuration: MetricConfiguration
    records_discovered: int = Field(ge=0)
    eligible_records: int = Field(ge=0)
    eligible_example_ids: list[StrictStr] = Field(default_factory=list)
    excluded_records: int = Field(ge=0)
    invalid_pair_records: int = Field(ge=0)
    assisted_input_categories: dict[str, int] = Field(default_factory=dict)
    exclusion_reasons: list[ExclusionCount]
    readiness_diagnostic_counts: dict[str, int]
    orphan_pair_results: int = Field(ge=0)
    arms: dict[Literal["direct", "assisted"], ArmEvaluationSummary]
    matched_output_pairs: int = Field(ge=0)
    execution_order_counts: dict[str, int]
    invocation_trace_counts: dict[str, int]
    paired_aggregate_differences: MetricScores
    per_example_order_counts: dict[str, dict[str, int]]
    per_example_comparisons: list[PerExampleComparison] = Field(default_factory=list)
    human_semantic_preservation: dict[str, str | int] = Field(
        default_factory=lambda: {
            "status": "deferred",
            "reason": "No genuine human-judgment artifact schema is available.",
        }
    )
    warnings: list[str] = Field(default_factory=list)
