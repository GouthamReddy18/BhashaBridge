"""Pure evaluation and aggregation over eligible annotations and paired runs."""
from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence
from typing import Literal

from app.schemas.evaluation import (
    ArmEvaluationSummary,
    EvaluationReport,
    ExclusionCount,
    MetricConfiguration,
    MetricPopulation,
    MetricScores,
    PairedEvaluationArtifact,
    PerExampleComparison,
)
from app.services.evaluation_metrics import METRIC_CONFIGURATION, corpus_bleu, corpus_chrf
from app.services.evaluation_readiness import EvaluationReadinessReport
from app.services.google_translation import PROVIDER_ID as RESEARCH_PROVIDER_ID

Split = Literal["train", "validation", "test"]
OUTCOME_KEYS = ("success", "failed", "unavailable", "disabled", "missing", "invalid")
FAILURE_CODES = (
    "provider_error", "invalid_provider_output", "provider_metadata_error",
    "provider_timeout", "provider_auth_error", "provider_quota_error",
    "provider_request_error", "provider_response_error", "provider_configuration_error",
    "mock_provider_test_only", "unregistered_provider_test_only", "contradictory_provider_metadata",
    "incompatible_provider_configuration",
    "split_metadata_mismatch",
)
ASSISTED_INPUT_CATEGORIES = (
    "identity", "normalization_only", "synthetic_transformation",
    "verified_transformation", "fallback", "other",
    "missing_artifact", "invalid_pair",
)
_SAFE_PROVIDER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SAFE_PROVIDER_MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
_SECRET_MARKER = re.compile(r"(?:api.?key|secret|token|password|^sk-)", re.IGNORECASE)
_SAFE_DATASET_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,79}$")


def _safe_provider_id(value: str | None) -> str | None:
    if value is None or not _SAFE_PROVIDER_ID.fullmatch(value) or _SECRET_MARKER.search(value):
        return None
    return value


def _safe_provider_model(value: str | None) -> str | None:
    if value is None or not _SAFE_PROVIDER_MODEL.fullmatch(value) or _SECRET_MARKER.search(value):
        return None
    return value


def _diagnostic_category(message: str) -> str:
    text = message.lower()
    if "duplicate record id" in text:
        return "duplicate_id"
    if "reference_translation" in text:
        return "reference_translation"
    if "intended_meaning" in text:
        return "intended_meaning"
    if "provenance" in text or "source_reference" in text:
        return "provenance"
    if "review" in text or "reviewed" in text:
        return "review_metadata"
    if "split" in text or "group" in text or "crosses" in text or "duplicate normalized" in text:
        return "split_or_leakage"
    if "tokens" in text or "telugu_romanized" in text or "english tokens" in text:
        return "test_population"
    return "structural_or_metadata"


def _difference(assisted: float | None, direct: float | None) -> float | None:
    if assisted is None or direct is None:
        return None
    return assisted - direct


def _population(name: str, references: list[str], hypotheses: list[str]) -> MetricPopulation:
    return MetricPopulation(
        denominator=name,
        examples=len(hypotheses),
        scores=MetricScores(
            bleu=corpus_bleu(references, hypotheses),
            chrf=corpus_chrf(references, hypotheses),
        ),
    )


def evaluate_paired_records(
    *,
    dataset_label: str,
    split: Split,
    annotation_rows: Sequence[tuple[int, dict]],
    readiness: EvaluationReadinessReport,
    paired_artifacts: Sequence[PairedEvaluationArtifact],
    include_per_example: bool = False,
    metric_configuration: MetricConfiguration = METRIC_CONFIGURATION,
) -> EvaluationReport:
    """Evaluate validated input artifacts without altering either input.

    A dataset with any blocking readiness diagnostic fails the whole-dataset
    gate and yields no scores. Once ready, each selected-split annotation stays
    in the operational denominator even when a paired result is absent/fails.
    """
    if metric_configuration != METRIC_CONFIGURATION:
        raise ValueError("unsupported metric configuration")
    if not _SAFE_DATASET_LABEL.fullmatch(dataset_label) or _SECRET_MARKER.search(dataset_label):
        raise ValueError("dataset_label must be a short safe label without paths or secret-like content")
    if readiness.records_examined != len(annotation_rows):
        raise ValueError("readiness report does not match the supplied annotation rows")
    annotation_ids = [row.get("id") for _, row in annotation_rows]
    if any(not isinstance(value, str) or not value.strip() for value in annotation_ids):
        raise ValueError("annotation rows require nonblank IDs")
    if len(annotation_ids) != len(set(annotation_ids)):
        raise ValueError("annotation rows must have unique IDs")

    by_id: dict[str, PairedEvaluationArtifact] = {}
    for artifact in paired_artifacts:
        if artifact.example_id in by_id:
            raise ValueError("duplicate paired artifact IDs are not allowed")
        by_id[artifact.example_id] = artifact

    known_ids = {
        row.get("id") for _, row in annotation_rows if isinstance(row.get("id"), str)
    }
    orphan_count = len(set(by_id) - known_ids)
    selected = [
        (line, row) for line, row in annotation_rows
        if row.get("split") == split
    ]
    selected.sort(key=lambda item: str(item[1].get("id", "")))
    readiness_errors = list(readiness.errors)
    diagnostic_counts = Counter(_diagnostic_category(issue.message) for issue in readiness_errors)
    exclusion_counts: Counter[str] = Counter()

    if readiness_errors:
        blocked_rows = list(annotation_rows)
        reasons_by_line: dict[int, set[str]] = {line: set() for line, _ in blocked_rows}
        for issue in readiness_errors:
            if issue.line in reasons_by_line:
                reasons_by_line[issue.line].add(_diagnostic_category(issue.message))
        for line, _row in blocked_rows:
            if reasons_by_line[line]:
                for reason in reasons_by_line[line]:
                    exclusion_counts[reason] += 1
            else:
                # The checker is a dataset-level gate; a blocking issue in
                # another partition also prevents scoring this dataset file.
                exclusion_counts["dataset_not_ready"] += 1
        empty_arms = {
            arm: ArmEvaluationSummary(
                outcome_counts={key: 0 for key in OUTCOME_KEYS},
                failure_code_counts={code: 0 for code in FAILURE_CODES},
                confirmed_provider_ids=[],
                confirmed_provider_models=[],
                available_output_example_ids=[],
                attempted_invocations=0,
                pre_invocation_failures=0,
                available_output_population=_population("successful_nonblank_outputs", [], []),
                matched_pair_population=_population("matched_successful_pairs", [], []),
            )
            for arm in ("direct", "assisted")
        }
        return EvaluationReport(
            evaluation_status="not_evaluated",
            dataset_label=dataset_label,
            split=split,
            metric_configuration=metric_configuration,
            records_discovered=len(annotation_rows),
            eligible_records=0,
            excluded_records=len(blocked_rows),
            invalid_pair_records=0,
            exclusion_reasons=[ExclusionCount(reason=key, examples=value) for key, value in sorted(exclusion_counts.items())],
            readiness_diagnostic_counts=dict(sorted(diagnostic_counts.items())),
            orphan_pair_results=orphan_count,
            arms=empty_arms,
            matched_output_pairs=0,
            execution_order_counts={"direct_first": 0, "assisted_first": 0},
            invocation_trace_counts={},
            paired_aggregate_differences=MetricScores(),
            per_example_order_counts={
                metric: {"higher": 0, "lower": 0, "equal": 0, "denominator": 0}
                for metric in ("bleu", "chrf")
            },
            warnings=["Dataset readiness failed; all metric populations are suppressed."],
        )

    eligible = selected
    eligible_by_id = {row.get("id"): row for _, row in eligible}
    outcome_counts = {
        arm: {key: 0 for key in OUTCOME_KEYS} for arm in ("direct", "assisted")
    }
    assistance_counts = {key: 0 for key in ASSISTED_INPUT_CATEGORIES}
    failure_counts = {
        arm: {code: 0 for code in FAILURE_CODES} for arm in ("direct", "assisted")
    }
    providers: dict[str, set[str]] = {"direct": set(), "assisted": set()}
    models: dict[str, set[str]] = {"direct": set(), "assisted": set()}
    attempted_invocations = {"direct": 0, "assisted": 0}
    pre_invocation_failures = {"direct": 0, "assisted": 0}
    execution_order_counts = {"direct_first": 0, "assisted_first": 0}
    invocation_trace_counts: Counter[str] = Counter()
    available: dict[str, list[tuple[str, str, str]]] = {"direct": [], "assisted": []}
    matched: list[tuple[str, str, str, str]] = []
    per_example: list[PerExampleComparison] = []
    order_counts = {
        metric: {"higher": 0, "lower": 0, "equal": 0, "denominator": 0}
        for metric in ("bleu", "chrf")
    }
    failure_warnings = 0
    invalid_pair_records = 0
    baseline_requested_configuration = None
    confirmed_provider_profile = None
    confirmed_model_profile = None

    for example_id, row in sorted(eligible_by_id.items(), key=lambda item: str(item[0])):
        artifact = by_id.get(example_id)
        if artifact is None:
            for arm in ("direct", "assisted"):
                outcome_counts[arm]["missing"] += 1
            assistance_counts["missing_artifact"] += 1
            continue
        result = artifact.result
        if artifact.split is not None and artifact.split != row.get("split"):
            for arm in ("direct", "assisted"):
                outcome_counts[arm]["invalid"] += 1
                failure_counts[arm]["split_metadata_mismatch"] += 1
            invalid_pair_records += 1
            assistance_counts["invalid_pair"] += 1
            continue
        execution_order_counts[result.configuration.execution_order] += 1
        invocation_trace = ",".join(result.invocation_order) or "none"
        invocation_trace_counts[invocation_trace] += 1
        for arm in ("direct", "assisted"):
            translation = getattr(result, arm).translation
            if translation.input_text is not None:
                attempted_invocations[arm] += 1
            elif translation.status == "failed":
                pre_invocation_failures[arm] += 1
            if translation.error_code in failure_counts[arm]:
                failure_counts[arm][translation.error_code] += 1
            if translation.status == "failed":
                failure_warnings += 1
        direct_provider = result.direct.translation.provider_id
        assisted_provider = result.assisted.translation.provider_id
        provider_mismatch = (
            direct_provider is not None
            and assisted_provider is not None
            and direct_provider != assisted_provider
        )
        requested_configuration = (
            result.configuration.target_language,
            result.configuration.requested_model,
            tuple(sorted(result.configuration.requested_generation_settings.items())),
            result.provider_configuration_forwarded,
        )
        provider_candidates = {value for value in (direct_provider, assisted_provider) if value is not None}
        configuration_mismatch = (
            baseline_requested_configuration is not None
            and requested_configuration != baseline_requested_configuration
        )
        provider_profile_mismatch = (
            confirmed_provider_profile is not None
            and any(value != confirmed_provider_profile for value in provider_candidates)
        )
        successful_models = {
            arm: getattr(result, arm).provider_confirmed.model
            if getattr(result, arm).translation.status == "success" else None
            for arm in ("direct", "assisted")
        }
        safe_models = {
            arm: _safe_provider_model(model) if model is not None else None
            for arm, model in successful_models.items()
        }
        unsafe_model_metadata = any(model is not None and safe_models[arm] is None for arm, model in successful_models.items())
        arm_model_mismatch = (
            safe_models["direct"] is not None
            and safe_models["assisted"] is not None
            and safe_models["direct"] != safe_models["assisted"]
        )
        requested_model_mismatch = (
            result.provider_configuration_forwarded
            and result.configuration.requested_model is not None
            and any(model is not None and model != result.configuration.requested_model for model in safe_models.values())
        )
        model_profile_mismatch = (
            confirmed_model_profile is not None
            and any(model is not None and model != confirmed_model_profile for model in safe_models.values())
        )
        if (
            result.original_input != row.get("text")
            or provider_mismatch
            or arm_model_mismatch
            or unsafe_model_metadata
            or requested_model_mismatch
            or configuration_mismatch
            or provider_profile_mismatch
            or model_profile_mismatch
        ):
            for arm in ("direct", "assisted"):
                outcome_counts[arm]["invalid"] += 1
                if provider_mismatch or arm_model_mismatch:
                    failure_counts[arm]["contradictory_provider_metadata"] += 1
                if (configuration_mismatch or provider_profile_mismatch or model_profile_mismatch
                        or requested_model_mismatch or unsafe_model_metadata):
                    failure_counts[arm]["incompatible_provider_configuration"] += 1
            invalid_pair_records += 1
            assistance_counts["invalid_pair"] += 1
            continue
        assistance = result.assisted_input
        if assistance.fallback:
            assistance_category = "fallback"
        elif assistance.transformations and all(
            item.evidence_status == "synthetic_fixture" for item in assistance.transformations
        ):
            assistance_category = "synthetic_transformation"
        elif assistance.meaningful_assistance:
            assistance_category = "verified_transformation"
        elif assistance.normalization_only:
            assistance_category = "normalization_only"
        elif assistance.assisted_input_equals_original:
            assistance_category = "identity"
        else:
            assistance_category = "other"
        assistance_counts[assistance_category] += 1
        if baseline_requested_configuration is None:
            baseline_requested_configuration = requested_configuration
        if confirmed_provider_profile is None and provider_candidates:
            confirmed_provider_profile = sorted(provider_candidates)[0]
        pair_models = {model for model in safe_models.values() if model is not None}
        if confirmed_model_profile is None and pair_models:
            confirmed_model_profile = sorted(pair_models)[0]

        successful: dict[str, tuple[str, str]] = {}
        for arm in ("direct", "assisted"):
            translation = getattr(result, arm).translation
            if translation.status == "success" and translation.provider_id != RESEARCH_PROVIDER_ID:
                outcome_counts[arm]["invalid"] += 1
                code = "mock_provider_test_only" if translation.provider_id == "mock.test" else "unregistered_provider_test_only"
                failure_counts[arm][code] += 1
                continue
            outcome_counts[arm][translation.status] += 1
            provider_id = _safe_provider_id(translation.provider_id)
            if provider_id == RESEARCH_PROVIDER_ID:
                providers[arm].add(provider_id)
            if translation.status == "success" and safe_models[arm] is not None:
                models[arm].add(safe_models[arm])
            if translation.status == "success" and translation.translated_text:
                successful[arm] = (row["reference_translation"], translation.translated_text)
                available[arm].append((str(example_id), *successful[arm]))
        if "direct" in successful and "assisted" in successful:
            ref, direct_text = successful["direct"]
            _, assisted_text = successful["assisted"]
            matched.append((str(example_id), ref, direct_text, assisted_text))
            direct_bleu = corpus_bleu([ref], [direct_text])
            assisted_bleu = corpus_bleu([ref], [assisted_text])
            direct_chrf = corpus_chrf([ref], [direct_text])
            assisted_chrf = corpus_chrf([ref], [assisted_text])
            for metric, direct_score, assisted_score in (
                ("bleu", direct_bleu, assisted_bleu),
                ("chrf", direct_chrf, assisted_chrf),
            ):
                relation = "equal" if math.isclose(direct_score, assisted_score, abs_tol=1e-12) else (
                    "higher" if assisted_score > direct_score else "lower"
                )
                order_counts[metric][relation] += 1
                order_counts[metric]["denominator"] += 1
            if include_per_example:
                per_example.append(PerExampleComparison(
                    example_id=str(example_id),
                    bleu_direct=direct_bleu,
                    bleu_assisted=assisted_bleu,
                    bleu_assisted_minus_direct=assisted_bleu - direct_bleu,
                    chrf_direct=direct_chrf,
                    chrf_assisted=assisted_chrf,
                    chrf_assisted_minus_direct=assisted_chrf - direct_chrf,
                ))

    available_populations: dict[str, MetricPopulation] = {}
    matched_populations: dict[str, MetricPopulation] = {}
    for arm in ("direct", "assisted"):
        arm_rows = available[arm]
        available_populations[arm] = _population(
            "eligible_records_with_successful_nonblank_output",
            [item[1] for item in arm_rows], [item[2] for item in arm_rows],
        )
        if arm == "direct":
            refs = [item[1] for item in matched]
            hyps = [item[2] for item in matched]
        else:
            refs = [item[1] for item in matched]
            hyps = [item[3] for item in matched]
        matched_populations[arm] = _population("same_IDs_successful_in_both_arms", refs, hyps)

    direct_matched = matched_populations["direct"].scores
    assisted_matched = matched_populations["assisted"].scores
    metric_population_exists = any(available[arm] for arm in ("direct", "assisted"))
    report_warnings = [
        "Corpus BLEU/chrF are reference-based proxies, not semantic-preservation judgments.",
        "Per-example metric order counts are exploratory and are not individual meaning judgments.",
        "No significance testing or human semantic-preservation aggregation is performed.",
        "Outputs from the project's mock.test provider are counted invalid and never scored.",
        "Requested model settings are checked separately from provider-returned model metadata; target language is not provider-confirmed.",
    ]
    if failure_warnings:
        report_warnings.append(f"{failure_warnings} provider failures remain in operational counts; they were not scored.")

    return EvaluationReport(
        evaluation_status="evaluated" if metric_population_exists else "no_metric_population",
        dataset_label=dataset_label,
        split=split,
        metric_configuration=metric_configuration,
        records_discovered=len(annotation_rows),
        eligible_records=len(eligible),
        eligible_example_ids=sorted(str(example_id) for example_id in eligible_by_id),
        excluded_records=len(annotation_rows) - len(eligible),
        invalid_pair_records=invalid_pair_records,
        assisted_input_categories=assistance_counts,
        exclusion_reasons=[
            ExclusionCount(reason="outside_requested_split", examples=len(annotation_rows) - len(eligible))
        ] if len(annotation_rows) != len(eligible) else [],
        readiness_diagnostic_counts={},
        orphan_pair_results=orphan_count,
        arms={
            arm: ArmEvaluationSummary(
                outcome_counts=outcome_counts[arm],
                failure_code_counts=failure_counts[arm],
                confirmed_provider_ids=sorted(providers[arm]),
                confirmed_provider_models=sorted(models[arm]),
                available_output_example_ids=sorted(item[0] for item in available[arm]),
                attempted_invocations=attempted_invocations[arm],
                pre_invocation_failures=pre_invocation_failures[arm],
                available_output_population=available_populations[arm],
                matched_pair_population=matched_populations[arm],
            )
            for arm in ("direct", "assisted")
        },
        matched_output_pairs=len(matched),
        execution_order_counts=execution_order_counts,
        invocation_trace_counts=dict(sorted(invocation_trace_counts.items())),
        paired_aggregate_differences=MetricScores(
            bleu=_difference(assisted_matched.bleu, direct_matched.bleu),
            chrf=_difference(assisted_matched.chrf, direct_matched.chrf),
        ),
        per_example_order_counts=order_counts,
        per_example_comparisons=per_example,
        warnings=report_warnings,
    )
