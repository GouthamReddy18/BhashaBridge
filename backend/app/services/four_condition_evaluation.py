"""Versioned, ID-matched descriptive evaluation for four-condition artifacts."""
from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import ValidationError

from app.schemas.evaluation import MetricScores
from app.schemas.four_condition import (
    ConditionComparison, ConditionEvaluationSummary, FourConditionArtifact,
    FourConditionEvaluationReport,
)
from app.services.evaluation_metrics import METRIC_CONFIGURATION, corpus_bleu, corpus_chrf
from app.services.evaluation_readiness import EvaluationReadinessReport
from app.services.four_condition_experiment import CONDITION_IDS

OUTCOMES = (
    "success", "provider_failed", "provider_unavailable", "blocked",
    "construction_failed", "missing_artifact", "invalid_pair",
    "mock_provider_output", "test_fixture_only",
)
COMPARISON_PAIRS = (
    ("normalized_v1", "direct_v1"),
    ("transliterated_v1", "normalized_v1"),
    ("ambiguity_aware_v1", "transliterated_v1"),
    ("transliterated_v1", "direct_v1"),
    ("ambiguity_aware_v1", "direct_v1"),
)


class FourConditionEvaluationError(ValueError):
    pass


def _scores(references: list[str], hypotheses: list[str]) -> MetricScores:
    if not references:
        return MetricScores()
    return MetricScores(bleu=corpus_bleu(references, hypotheses), chrf=corpus_chrf(references, hypotheses))


def _comparison_id(numerator: str, denominator: str) -> str:
    return f"{numerator}-minus-{denominator}"


def _difference(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None:
        return None
    return numerator - denominator


def evaluate_four_condition_records(
    *,
    dataset_label: str,
    split: str,
    annotation_rows: Sequence[tuple[int, dict]],
    readiness: EvaluationReadinessReport,
    artifacts: Sequence[FourConditionArtifact],
) -> FourConditionEvaluationReport:
    """Score only eligible IDs, retaining blocked and unavailable conditions."""
    if dataset_label.strip() == "" or len(dataset_label) > 80:
        raise FourConditionEvaluationError("dataset_label is invalid")
    if readiness.records_examined != len(annotation_rows):
        raise FourConditionEvaluationError("readiness result does not match annotations")
    annotation_by_id = {}
    for _line, row in annotation_rows:
        example_id = row.get("id")
        if not isinstance(example_id, str) or not example_id.strip() or example_id in annotation_by_id:
            raise FourConditionEvaluationError("annotation IDs must be nonblank and unique")
        annotation_by_id[example_id] = row
    by_id = {}
    validated_artifacts = []
    for artifact in artifacts:
        try:
            artifact = FourConditionArtifact.model_validate(artifact.model_dump(mode="python"))
        except (ValidationError, AttributeError, TypeError):
            raise FourConditionEvaluationError("four-condition artifact failed integrity validation") from None
        validated_artifacts.append(artifact)
        if artifact.example_id in by_id:
            raise FourConditionEvaluationError("duplicate four-condition artifact IDs")
        by_id[artifact.example_id] = artifact
    artifacts = validated_artifacts
    selected = {key: row for key, row in annotation_by_id.items() if row.get("split") == split}
    if any(key not in annotation_by_id for key in by_id):
        raise FourConditionEvaluationError("artifacts contain IDs absent from the annotation dataset")
    if any(key in annotation_by_id and annotation_by_id[key].get("split") != split for key in by_id):
        raise FourConditionEvaluationError("artifacts contain IDs outside the selected split")
    eligible_ids = sorted(selected) if readiness.ready else []
    if not readiness.ready:
        eligible_ids = []
    discovered = len(annotation_rows)
    eligible_count = len(eligible_ids)
    excluded_count = discovered - eligible_count
    diagnostic_counts = Counter(
        "dataset_readiness_blocked" for _ in readiness.errors
    )
    artifact_fingerprints = {item.configuration.fingerprint for item in artifacts}
    if len(artifact_fingerprints) > 1:
        raise FourConditionEvaluationError("artifact experiment configurations are incompatible")
    fingerprint = next(iter(artifact_fingerprints), None)
    for artifact in artifacts:
        if artifact.configuration.dataset_label != dataset_label or artifact.split != split:
            raise FourConditionEvaluationError("artifact dataset label or split does not match evaluation request")

    counts = {condition: Counter({key: 0 for key in OUTCOMES}) for condition in CONDITION_IDS}
    available: dict[str, dict[str, tuple[str, str]]] = {condition: {} for condition in CONDITION_IDS}
    test_fixture_report = False
    known_provider = None
    known_model = None
    known_forwarding = None
    has_known_forwarding = False
    invalid_ids: set[str] = set()

    # Validate row/source and provider consistency before assigning any score.
    for example_id in eligible_ids:
        artifact = by_id.get(example_id)
        if artifact is None:
            continue
        row = selected[example_id]
        result = artifact.result
        if result.original_input != row.get("text"):
            invalid_ids.add(example_id)
            continue
        provider_ids = set()
        provider_models = set()
        forwarding_values = set()
        malformed = False
        for item in result.conditions:
            translation = item.translation
            if translation is None:
                continue
            if translation.provider_id:
                provider_ids.add(translation.provider_id)
            if translation.input_text is not None:
                forwarding_values.add(translation.provider_configuration_forwarded)
            if translation.status == "success" and translation.provider_id:
                if translation.provider_model:
                    provider_models.add(translation.provider_model)
        if len(provider_ids) > 1 or len(provider_models) > 1:
            malformed = True
        if len(forwarding_values) > 1:
            malformed = True
        if forwarding_values:
            forwarding = next(iter(forwarding_values))
            if has_known_forwarding and forwarding != known_forwarding:
                malformed = True
            elif not has_known_forwarding:
                known_forwarding = forwarding
                has_known_forwarding = True
        if provider_models and result.configuration.requested_model is not None and forwarding_values == {True}:
            if any(model != result.configuration.requested_model for model in provider_models):
                malformed = True
        if provider_ids:
            provider_id = next(iter(provider_ids))
            if known_provider is not None and provider_id != known_provider:
                malformed = True
            known_provider = known_provider or provider_id
        if provider_models:
            model = next(iter(provider_models))
            if known_model is not None and model != known_model:
                malformed = True
            known_model = known_model or model
        if malformed:
            invalid_ids.add(example_id)

    for example_id in eligible_ids:
        artifact = by_id.get(example_id)
        for condition_id in CONDITION_IDS:
            if artifact is None:
                counts[condition_id]["missing_artifact"] += 1
                continue
            result = artifact.result
            condition = next(item for item in result.conditions if item.condition_id == condition_id)
            if example_id in invalid_ids:
                counts[condition_id]["invalid_pair"] += 1
                continue
            if result.test_fixture:
                test_fixture_report = True
                counts[condition_id]["test_fixture_only"] += 1
                continue
            if condition.status == "blocked":
                counts[condition_id]["blocked"] += 1
                continue
            if condition.status == "failed":
                counts[condition_id]["construction_failed"] += 1
                continue
            translation = condition.translation
            if translation is None:
                counts[condition_id]["construction_failed"] += 1
            elif translation.status == "unavailable":
                counts[condition_id]["provider_unavailable"] += 1
            elif translation.status == "failed":
                counts[condition_id]["provider_failed"] += 1
            elif translation.status == "success" and translation.provider_id == "mock.test":
                counts[condition_id]["mock_provider_output"] += 1
                test_fixture_report = True
            elif translation.status == "success":
                if not condition.research_eligible:
                    counts[condition_id]["test_fixture_only"] += 1
                    test_fixture_report = True
                    continue
                counts[condition_id]["success"] += 1
                available[condition_id][example_id] = (
                    selected[example_id]["reference_translation"], translation.translated_text,
                )
            else:
                counts[condition_id]["provider_failed"] += 1

    summaries = {}
    for condition_id in CONDITION_IDS:
        rows = available[condition_id]
        ids = sorted(rows)
        excluded_ids = sorted(set(eligible_ids) - set(ids))
        summaries[condition_id] = ConditionEvaluationSummary(
            outcome_counts=dict(counts[condition_id]),
            available_example_ids=tuple(ids),
            available_examples=len(ids),
            excluded_example_ids=tuple(excluded_ids),
            scores=_scores([rows[key][0] for key in ids], [rows[key][1] for key in ids]),
            blocked_conditions=counts[condition_id]["blocked"],
            research_eligible=not test_fixture_report and all(
                by_id[key].result.conditions[index].research_eligible
                for key in ids for index, item in enumerate(by_id[key].result.conditions)
                if item.condition_id == condition_id
            ),
        )

    comparisons = []
    for numerator, denominator in COMPARISON_PAIRS:
        matched_ids = sorted(set(available[numerator]) & set(available[denominator]))
        excluded_ids = sorted(set(eligible_ids) - set(matched_ids))
        refs = [selected[key]["reference_translation"] for key in matched_ids]
        numerator_scores = _scores(refs, [available[numerator][key][1] for key in matched_ids])
        denominator_scores = _scores(refs, [available[denominator][key][1] for key in matched_ids])
        comparisons.append(ConditionComparison(
            comparison_id=_comparison_id(numerator, denominator),
            numerator_condition=numerator,
            denominator_condition=denominator,
            matched_example_ids=tuple(matched_ids),
            matched_examples=len(matched_ids),
            excluded_example_ids=tuple(excluded_ids),
            numerator_scores=numerator_scores,
            denominator_scores=denominator_scores,
            numerator_minus_denominator=MetricScores(
                bleu=_difference(numerator_scores.bleu, denominator_scores.bleu),
                chrf=_difference(numerator_scores.chrf, denominator_scores.chrf),
            ),
        ))

    any_available = any(available[item] for item in CONDITION_IDS)
    report_status = (
        "not_evaluated" if not readiness.ready
        else "test_fixture_only" if test_fixture_report
        else "evaluated" if any_available
        else "no_metric_population"
    )
    return FourConditionEvaluationReport(
        schema_version="1.0",
        report_status=report_status,
        dataset_label=dataset_label,
        split=split,
        experiment_version="four_condition.v1",
        configuration_fingerprint=fingerprint,
        metric_configuration=METRIC_CONFIGURATION,
        records_discovered=discovered,
        eligible_records=eligible_count,
        eligible_example_ids=tuple(eligible_ids),
        excluded_records=excluded_count,
        orphan_artifacts=0,
        readiness_diagnostic_counts=dict(sorted(diagnostic_counts.items())),
        variants=summaries,
        comparisons=tuple(comparisons),
        limitations=(
            "Only corpus BLEU/chrF descriptive proxies are reported; no semantic score, significance test, or causal claim is produced.",
            "Condition configurations and resource review metadata are caller declarations and are not independently authenticated.",
            "Blocked, missing, unavailable, failed, invalid, and mock-provider outcomes are never converted into scores.",
            "The current project has no genuine eligible dataset or reviewed production normalization, transliteration, or contextual resources.",
        ),
    )


def validate_four_condition_report(value: object):
    """Validate schema, denominators, comparisons, and metric differences."""
    from app.schemas.four_condition import FourConditionEvaluationReport

    if not isinstance(value, Mapping):
        return False, ("report must be a JSON object",)
    try:
        # JSON arrays are decoded as lists while the immutable contract uses tuples.
        report = FourConditionEvaluationReport.model_validate(value)
    except ValidationError as exc:
        return False, tuple(sorted(f"schema:{item['type']}" for item in exc.errors()))
    errors = []
    conditions = set(CONDITION_IDS)
    if set(report.variants) != conditions:
        errors.append("variant set must contain exactly the four registered IDs")
    if report.eligible_records + report.excluded_records != report.records_discovered:
        errors.append("eligible and excluded counts must sum to discovered records")
    if any(not isinstance(value, int) or value < 0 for value in report.readiness_diagnostic_counts.values()):
        errors.append("readiness diagnostic counts must be nonnegative integers")
    if tuple(report.eligible_example_ids) != tuple(sorted(set(report.eligible_example_ids))) or len(report.eligible_example_ids) != report.eligible_records:
        errors.append("eligible IDs must be sorted, unique, and match the denominator")
    eligible = set(report.eligible_example_ids)
    for condition_id, summary in report.variants.items():
        for value in (summary.scores.bleu, summary.scores.chrf):
            if value is not None and (not math.isfinite(value) or not 0 <= value <= 100):
                errors.append(f"{condition_id}: scores must be finite and within 0..100")
        if set(summary.outcome_counts) != set(OUTCOMES):
            errors.append(f"{condition_id}: outcome keys are invalid")
        if any(not isinstance(value, int) or value < 0 for value in summary.outcome_counts.values()):
            errors.append(f"{condition_id}: outcome counts must be nonnegative integers")
        if sum(summary.outcome_counts.values()) != report.eligible_records:
            errors.append(f"{condition_id}: outcome denominator does not reconcile")
        if summary.available_examples != len(summary.available_example_ids):
            errors.append(f"{condition_id}: available-output count does not reconcile")
        if tuple(summary.available_example_ids) != tuple(sorted(set(summary.available_example_ids))):
            errors.append(f"{condition_id}: available IDs are not canonical")
        if set(summary.available_example_ids) - eligible:
            errors.append(f"{condition_id}: available IDs are outside the eligible population")
        if set(summary.excluded_example_ids) != eligible - set(summary.available_example_ids):
            errors.append(f"{condition_id}: excluded IDs do not reconcile")
        if summary.blocked_conditions != summary.outcome_counts.get("blocked", 0):
            errors.append(f"{condition_id}: blocked count does not reconcile")
        if summary.available_examples == 0 and (summary.scores.bleu is not None or summary.scores.chrf is not None):
            errors.append(f"{condition_id}: empty population cannot have scores")
        if summary.available_examples and (summary.scores.bleu is None or summary.scores.chrf is None):
            errors.append(f"{condition_id}: nonempty population requires BLEU and chrF")
        if summary.outcome_counts.get("success", 0) != summary.available_examples:
            errors.append(f"{condition_id}: success count must equal available output count")
    expected_pairs = tuple(_comparison_id(*pair) for pair in COMPARISON_PAIRS)
    if tuple(item.comparison_id for item in report.comparisons) != expected_pairs:
        errors.append("comparison list must contain the five stable adjacent/baseline comparisons in order")
    for comparison, (expected_numerator, expected_denominator) in zip(report.comparisons, COMPARISON_PAIRS):
        if (comparison.numerator_condition, comparison.denominator_condition) != (expected_numerator, expected_denominator):
            errors.append(f"{comparison.comparison_id}: condition references do not match the registered comparison")
        matched = set(comparison.matched_example_ids)
        if tuple(comparison.matched_example_ids) != tuple(sorted(matched)) or len(matched) != comparison.matched_examples:
            errors.append(f"{comparison.comparison_id}: matched IDs/count do not reconcile")
        if not matched <= eligible:
            errors.append(f"{comparison.comparison_id}: matched IDs exceed the eligible population")
        expected_matched = (
            set(report.variants[comparison.numerator_condition].available_example_ids)
            & set(report.variants[comparison.denominator_condition].available_example_ids)
        )
        if matched != expected_matched:
            errors.append(f"{comparison.comparison_id}: matched IDs must equal the intersection of available outputs")
        if set(comparison.excluded_example_ids) != eligible - matched:
            errors.append(f"{comparison.comparison_id}: excluded IDs do not reconcile")
        for metric in ("bleu", "chrf"):
            numerator = getattr(comparison.numerator_scores, metric)
            denominator = getattr(comparison.denominator_scores, metric)
            difference = getattr(comparison.numerator_minus_denominator, metric)
            if comparison.matched_examples == 0:
                if any(x is not None for x in (numerator, denominator, difference)):
                    errors.append(f"{comparison.comparison_id}: empty matched population cannot have scores")
            elif numerator is None or denominator is None or difference is None:
                errors.append(f"{comparison.comparison_id}: nonempty population requires both scores and difference")
            elif any(not math.isfinite(x) for x in (numerator, denominator, difference)):
                errors.append(f"{comparison.comparison_id}: scores must be finite")
            elif not (0 <= numerator <= 100 and 0 <= denominator <= 100):
                errors.append(f"{comparison.comparison_id}: BLEU/chrF scores must be within 0..100")
            elif not math.isclose(difference, numerator - denominator, rel_tol=1e-9, abs_tol=1e-9):
                errors.append(f"{comparison.comparison_id}: score difference is inconsistent")
    if report.report_status == "not_evaluated":
        if report.eligible_records or report.eligible_example_ids or not report.readiness_diagnostic_counts:
            errors.append("not_evaluated report must suppress eligibility and include readiness diagnostics")
    if report.report_status == "no_metric_population" and any(v.available_examples for v in report.variants.values()):
        errors.append("no_metric_population report cannot contain available outputs")
    if report.report_status == "evaluated" and not any(v.available_examples for v in report.variants.values()):
        errors.append("evaluated report requires at least one available metric population")
    if report.report_status == "test_fixture_only" and not any(
        v.outcome_counts.get("test_fixture_only", 0) or v.outcome_counts.get("mock_provider_output", 0)
        for v in report.variants.values()
    ):
        errors.append("test_fixture_only report requires an explicitly tainted outcome")
    if report.human_semantic_preservation != "pending":
        errors.append("human scores are not supported by this report contract")
    return not errors, tuple(sorted(set(errors)))


def evaluate_four_condition_files(
    annotations_path: str | Path,
    artifacts_path: str | Path,
    *, dataset_label: str, split: str,
) -> FourConditionEvaluationReport:
    from app.services.dataset_validation import _unique_object_pairs, validate_dataset
    from app.services.evaluation_readiness import check_evaluation_readiness
    from app.schemas.four_condition import FourConditionArtifact

    structural = validate_dataset(annotations_path)
    if structural.errors:
        raise FourConditionEvaluationError("annotation structural validation failed")
    try:
        rows = []
        with Path(annotations_path).open(encoding="utf-8") as stream:
            for line_number, raw in enumerate(stream, 1):
                if raw.strip():
                    rows.append((line_number, json.loads(raw, object_pairs_hook=_unique_object_pairs)))
        artifacts = []
        with Path(artifacts_path).open(encoding="utf-8") as stream:
            for line_number, raw in enumerate(stream, 1):
                if not raw.strip():
                    continue
                value = json.loads(raw, object_pairs_hook=_unique_object_pairs)
                try:
                    # JSON arrays decode as lists while tuple fields represent immutable records.
                    artifacts.append(FourConditionArtifact.model_validate(value))
                except ValidationError as exc:
                    raise FourConditionEvaluationError(f"artifact line {line_number} has an invalid schema") from None
    except FourConditionEvaluationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        raise FourConditionEvaluationError("evaluation inputs could not be read safely") from None
    readiness = check_evaluation_readiness(annotations_path)
    return evaluate_four_condition_records(
        dataset_label=dataset_label, split=split, annotation_rows=rows,
        readiness=readiness, artifacts=artifacts,
    )
