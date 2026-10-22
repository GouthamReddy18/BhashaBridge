"""Structural and cross-field validation for serialized evaluation reports."""
from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictStr, ValidationError

from app.schemas.evaluation import EvaluationReport, MetricConfiguration
from app.services.evaluation_metrics import METRIC_CONFIGURATION
from app.services.google_translation import PROVIDER_ID as RESEARCH_PROVIDER_ID

ValidationStatus = Literal["VALID", "INVALID", "UNSUPPORTED_VERSION"]

_OUTCOMES = {"success", "failed", "unavailable", "disabled", "missing", "invalid"}
_LEGACY_FAILURES = {
    "provider_error", "invalid_provider_output", "provider_metadata_error",
    "mock_provider_test_only", "contradictory_provider_metadata",
    "unregistered_provider_test_only",
    "incompatible_provider_configuration",
}
_FAILURES = _LEGACY_FAILURES | {
    "provider_timeout", "provider_auth_error", "provider_quota_error",
    "provider_request_error", "provider_response_error", "provider_configuration_error",
    "split_metadata_mismatch",
}
_PRE_SPLIT_FAILURES = _FAILURES - {"split_metadata_mismatch"}
_ORDERS = {"direct_first", "assisted_first"}
_TRACES = {"none", "direct", "assisted", "direct,assisted", "assisted,direct"}
_METRICS = {"bleu", "chrf"}
_READINESS_CATEGORIES = {
    "duplicate_id", "reference_translation", "intended_meaning", "provenance",
    "review_metadata", "split_or_leakage", "test_population", "structural_or_metadata",
}
_EXCLUSION_CATEGORIES = _READINESS_CATEGORIES | {"dataset_not_ready", "outside_requested_split"}
_ASSISTANCE_CATEGORIES = {
    "identity", "normalization_only", "synthetic_transformation",
    "verified_transformation", "fallback", "other", "missing_artifact", "invalid_pair",
}
_SAFE_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,79}$")
_SAFE_PROVIDER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SAFE_PROVIDER_MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
_SECRET = re.compile(r"(?:api.?key|secret|token|password|^sk-)", re.IGNORECASE)
_SAFE_LOCATION_PART = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TOLERANCE = 1e-9


class EvaluationReportDiagnostic(BaseModel):
    """One sanitized, stable report validation diagnostic."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: StrictStr
    message: StrictStr
    location: StrictStr
    severity: Literal["error", "warning"] = "error"


class EvaluationReportValidationResult(BaseModel):
    """Validation result; VALID means contract consistency, not research proof."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: ValidationStatus
    diagnostics: tuple[EvaluationReportDiagnostic, ...] = ()


def _error(code: str, location: str, message: str) -> EvaluationReportDiagnostic:
    return EvaluationReportDiagnostic(code=code, location=location, message=message)


def _safe_location_part(value: object) -> str:
    if isinstance(value, int):
        return f"[{value}]"
    part = str(value)
    if _SAFE_LOCATION_PART.fullmatch(part) and not _SECRET.search(part):
        return ("." if part else "") + part
    return ".<key>"


def _version_status(value: object) -> EvaluationReportValidationResult | None:
    if not isinstance(value, Mapping):
        return None
    version = value.get("schema_version")
    if isinstance(version, str) and version != "1.0":
        return EvaluationReportValidationResult(
            status="UNSUPPORTED_VERSION",
            diagnostics=(_error("unsupported_schema_version", "schema_version", "Report schema version is not supported."),),
        )
    config = value.get("metric_configuration")
    if isinstance(config, Mapping):
        implementation = config.get("implementation")
        metric_version = config.get("version")
        if (isinstance(implementation, str) and implementation != METRIC_CONFIGURATION.implementation) or (
            isinstance(metric_version, str) and metric_version != METRIC_CONFIGURATION.version
        ):
            return EvaluationReportValidationResult(
                status="UNSUPPORTED_VERSION",
                diagnostics=(_error("unsupported_metric_version", "metric_configuration", "Metric implementation or version is not supported."),),
            )
    return None


def _finite_tree(value: object, location: str = "") -> list[EvaluationReportDiagnostic]:
    errors: list[EvaluationReportDiagnostic] = []
    if isinstance(value, float) and not math.isfinite(value):
        errors.append(_error("non_finite_number", location or "$", "Numeric values must be finite."))
    elif isinstance(value, Mapping):
        for key in sorted(value, key=str):
            child = location + _safe_location_part(key)
            errors.extend(_finite_tree(value[key], child))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            errors.extend(_finite_tree(item, location + f"[{index}]"))
    return errors


def _same(left: float | None, right: float | None) -> bool:
    if left is None or right is None:
        return left is right
    return math.isclose(left, right, rel_tol=_TOLERANCE, abs_tol=_TOLERANCE)


def _integrity_errors(report: EvaluationReport) -> list[EvaluationReportDiagnostic]:
    errors: list[EvaluationReportDiagnostic] = []

    def add(code: str, path: str, message: str) -> None:
        errors.append(_error(code, path, message))

    discovered, eligible, excluded = report.records_discovered, report.eligible_records, report.excluded_records
    if eligible + excluded != discovered:
        add("population_total_mismatch", "eligible_records", "Eligible and excluded records must sum to records_discovered.")
    if report.eligible_example_ids:
        if report.eligible_example_ids != sorted(set(report.eligible_example_ids)):
            add("eligible_ids_not_canonical", "eligible_example_ids", "Eligible example IDs must be unique and sorted.")
        if len(report.eligible_example_ids) != eligible:
            add("eligible_ids_denominator", "eligible_example_ids", "Eligible example IDs must match eligible_records.")

    if report.assisted_input_categories:
        if set(report.assisted_input_categories) != _ASSISTANCE_CATEGORIES:
            add("assistance_category_keys", "assisted_input_categories", "Assisted-input category keys must match the supported contract.")
        for key, count in report.assisted_input_categories.items():
            if count < 0:
                add("negative_count", "assisted_input_categories" + _safe_location_part(key), "Counts must be nonnegative integers.")
        if sum(report.assisted_input_categories.values()) != eligible:
            add("assistance_category_denominator", "assisted_input_categories", "Assisted-input categories must sum to eligible_records.")
    elif report.evaluation_status != "not_evaluated" and eligible:
        # Older serialized reports predate this additive Phase 11 diagnostic.
        pass

    for mapping_path, mapping in (
        ("readiness_diagnostic_counts", report.readiness_diagnostic_counts),
        ("execution_order_counts", report.execution_order_counts),
        ("invocation_trace_counts", report.invocation_trace_counts),
    ):
        for key, count in mapping.items():
            if count < 0:
                add("negative_count", mapping_path + _safe_location_part(key), "Counts must be nonnegative integers.")
    for key, count in report.readiness_diagnostic_counts.items():
        if key not in _READINESS_CATEGORIES or count == 0:
            add("readiness_diagnostic_value", "readiness_diagnostic_counts" + _safe_location_part(key), "Readiness diagnostics must use supported categories with positive counts.")

    if not _SAFE_LABEL.fullmatch(report.dataset_label) or _SECRET.search(report.dataset_label):
        add("unsafe_dataset_label", "dataset_label", "Dataset label must be a short safe identifier without secret-like content.")

    for arm_name in ("direct", "assisted"):
        arm = report.arms[arm_name]
        base = f"arms.{arm_name}"
        if set(arm.outcome_counts) != _OUTCOMES:
            add("outcome_keys", f"{base}.outcome_counts", "Outcome keys must match the supported report contract.")
            continue
        if set(arm.failure_code_counts) not in (_FAILURES, _PRE_SPLIT_FAILURES, _LEGACY_FAILURES):
            add("failure_code_keys", f"{base}.failure_code_counts", "Failure-code keys must match the supported report contract.")
        for key, count in arm.outcome_counts.items():
            if count < 0:
                add("negative_count", f"{base}.outcome_counts" + _safe_location_part(key), "Counts must be nonnegative integers.")
        for key, count in arm.failure_code_counts.items():
            if count < 0:
                add("negative_count", f"{base}.failure_code_counts" + _safe_location_part(key), "Counts must be nonnegative integers.")
        if arm.failure_code_counts.get("mock_provider_test_only", 0) > arm.outcome_counts.get("invalid", 0):
            add("mock_provider_outcome_mismatch", f"{base}.failure_code_counts.mock_provider_test_only", "Mock-provider successes must be counted as invalid outcomes, never successful evidence.")
        if arm.failure_code_counts.get("unregistered_provider_test_only", 0) > arm.outcome_counts.get("invalid", 0):
            add("unregistered_provider_outcome_mismatch", f"{base}.failure_code_counts.unregistered_provider_test_only", "Unregistered-provider successes must be counted as invalid outcomes, never successful evidence.")
        if sum(arm.outcome_counts.values()) != eligible:
            add("outcome_denominator_mismatch", f"{base}.outcome_counts", "Per-arm outcome counts must sum to eligible_records.")
        if arm.outcome_counts["success"] != arm.available_output_population.examples:
            add("success_population_mismatch", f"{base}.available_output_population.examples", "Successful outcome count must equal the available-output population.")
        if arm.available_output_example_ids:
            if arm.available_output_example_ids != sorted(set(arm.available_output_example_ids)):
                add("available_ids_not_canonical", f"{base}.available_output_example_ids", "Available-output IDs must be unique and sorted.")
            if len(arm.available_output_example_ids) != arm.available_output_population.examples:
                add("available_ids_denominator", f"{base}.available_output_example_ids", "Available-output IDs must match the successful output population.")
        if arm.outcome_counts["disabled"] != 0:
            add("disabled_outcome_unsupported", f"{base}.outcome_counts.disabled", "Paired experiment reports cannot contain disabled arm outcomes.")
        if arm.available_output_population.examples > eligible:
            add("population_exceeds_denominator", f"{base}.available_output_population.examples", "Available-output population cannot exceed eligible_records.")
        if arm.attempted_invocations + arm.pre_invocation_failures > eligible:
            add("invocation_count_exceeds_denominator", base, "Attempted calls and pre-invocation failures cannot exceed eligible_records.")
        if arm.pre_invocation_failures > arm.outcome_counts["failed"] + arm.outcome_counts["invalid"]:
            add("pre_invocation_failure_mismatch", f"{base}.pre_invocation_failures", "Pre-invocation failures must correspond to failed or invalid outcomes.")
        if arm.outcome_counts["invalid"] < report.invalid_pair_records:
            add("invalid_pair_count_mismatch", f"{base}.outcome_counts.invalid", "Every invalid pair must be counted as invalid in each arm.")

        available = arm.available_output_population
        matched = arm.matched_pair_population
        expected_available_denominator = (
            "successful_nonblank_outputs" if report.evaluation_status == "not_evaluated"
            else "eligible_records_with_successful_nonblank_output"
        )
        expected_matched_denominator = (
            "matched_successful_pairs" if report.evaluation_status == "not_evaluated"
            else "same_IDs_successful_in_both_arms"
        )
        if available.denominator != expected_available_denominator:
            add("population_denominator_label", f"{base}.available_output_population.denominator", "Available-output denominator label does not match the report contract.")
        if matched.denominator != expected_matched_denominator:
            add("population_denominator_label", f"{base}.matched_pair_population.denominator", "Matched-pair denominator label does not match the report contract.")
        for population_name, population in (("available_output_population", available), ("matched_pair_population", matched)):
            path = f"{base}.{population_name}"
            for metric in ("bleu", "chrf"):
                score = getattr(population.scores, metric)
                if population.examples == 0 and score is not None:
                    add("empty_population_has_score", f"{path}.scores.{metric}", "A zero-example metric population must have a null score.")
                elif population.examples > 0 and score is None:
                    add("nonempty_population_missing_score", f"{path}.scores.{metric}", "A nonempty metric population must have a score.")
                elif score is not None and not (0.0 <= score <= 100.0):
                    add("score_out_of_range", f"{path}.scores.{metric}", "Metric scores must be within the evaluator's 0–100 scale.")
        if matched.examples != report.matched_output_pairs:
            add("matched_population_mismatch", f"{base}.matched_pair_population.examples", "Arm matched population must equal matched_output_pairs.")
        if matched.examples > available.examples:
            add("matched_exceeds_available", f"{base}.matched_pair_population.examples", "Matched population cannot exceed the arm's available-output population.")

        ids = arm.confirmed_provider_ids
        if ids != sorted(set(ids)):
            add("provider_ids_not_canonical", f"{base}.confirmed_provider_ids", "Provider identifiers must be unique and sorted.")
        for index, provider_id in enumerate(ids):
            if not _SAFE_PROVIDER.fullmatch(provider_id) or _SECRET.search(provider_id) or provider_id != RESEARCH_PROVIDER_ID:
                add("unsafe_provider_id", f"{base}.confirmed_provider_ids[{index}]", "Provider identifier is unsafe or test-only.")
        model_ids = arm.confirmed_provider_models
        if model_ids != sorted(set(model_ids)):
            add("provider_models_not_canonical", f"{base}.confirmed_provider_models", "Confirmed provider models must be unique and sorted.")
        for index, model_id in enumerate(model_ids):
            if not _SAFE_PROVIDER_MODEL.fullmatch(model_id) or _SECRET.search(model_id):
                add("unsafe_provider_model", f"{base}.confirmed_provider_models[{index}]", "Confirmed provider model metadata is unsafe.")

    if report.matched_output_pairs > min(
        report.arms["direct"].available_output_population.examples,
        report.arms["assisted"].available_output_population.examples,
    ):
        add("matched_exceeds_arm_successes", "matched_output_pairs", "Matched pairs cannot exceed either arm's available-output population.")

    if set(report.execution_order_counts) != _ORDERS:
        add("execution_order_keys", "execution_order_counts", "Execution-order keys must match the supported values.")
    if set(report.invocation_trace_counts) - _TRACES:
        add("invocation_trace_value", "invocation_trace_counts", "Invocation traces contain an unsupported value.")
    artifact_count = sum(report.execution_order_counts.values())
    if artifact_count > eligible:
        add("artifact_count_exceeds_eligible", "execution_order_counts", "Paired artifacts in the selected split cannot exceed eligible_records.")
    if sum(report.invocation_trace_counts.values()) != artifact_count:
        add("invocation_trace_count_mismatch", "invocation_trace_counts", "Invocation traces must cover each selected paired artifact exactly once.")
    for arm_name in ("direct", "assisted"):
        arm = report.arms[arm_name]
        if arm.attempted_invocations + arm.pre_invocation_failures > artifact_count:
            add("invocation_count_exceeds_artifacts", f"arms.{arm_name}", "Attempted calls and pre-invocation failures cannot exceed paired artifacts.")
    missing_direct = report.arms["direct"].outcome_counts.get("missing", 0)
    missing_assisted = report.arms["assisted"].outcome_counts.get("missing", 0)
    if missing_direct != missing_assisted or artifact_count + missing_direct != eligible:
        add("missing_artifact_count_mismatch", "arms", "Missing artifacts must be counted for both arms and reconcile with selected paired artifacts.")

    if report.invalid_pair_records > artifact_count:
        add("invalid_pairs_exceed_artifacts", "invalid_pair_records", "Invalid pair count cannot exceed selected paired artifacts.")

    ready = not report.readiness_diagnostic_counts
    if not ready and report.evaluation_status != "not_evaluated":
        add("readiness_status_mismatch", "evaluation_status", "Readiness diagnostics require status not_evaluated.")
    if ready and report.evaluation_status == "not_evaluated":
        add("readiness_status_mismatch", "evaluation_status", "Status not_evaluated requires readiness diagnostics.")
    if report.evaluation_status == "not_evaluated":
        if eligible != 0 or excluded != discovered:
            add("not_evaluated_population_mismatch", "eligible_records", "A readiness-blocked report must suppress eligibility and exclude the discovered population.")
        if discovered > 0 and not report.exclusion_reasons:
            add("missing_readiness_exclusions", "exclusion_reasons", "A readiness-blocked report must identify at least one exclusion reason.")
        if discovered > 0 and sum(reason.examples for reason in report.exclusion_reasons) < excluded:
            add("readiness_exclusions_incomplete", "exclusion_reasons", "Readiness exclusion categories must cover every excluded record; category counts may overlap.")
        if report.matched_output_pairs != 0 or any(
            arm.available_output_population.examples != 0
            or arm.matched_pair_population.examples != 0
            for arm in report.arms.values()
        ):
            add("readiness_scores_not_suppressed", "arms", "A readiness-blocked report must suppress all metric populations.")
    else:
        if report.exclusion_reasons:
            if excluded == 0 or len(report.exclusion_reasons) != 1 or report.exclusion_reasons[0].reason != "outside_requested_split" or report.exclusion_reasons[0].examples != excluded:
                add("exclusion_count_mismatch", "exclusion_reasons", "A ready report may only count records outside the requested split, exactly matching excluded_records.")
        elif excluded != 0:
            add("exclusion_count_mismatch", "exclusion_reasons", "Excluded records require an outside_requested_split reason.")
    seen_exclusion_reasons: set[str] = set()
    for index, reason in enumerate(report.exclusion_reasons):
        if reason.reason not in _EXCLUSION_CATEGORIES:
            add("exclusion_reason", f"exclusion_reasons[{index}].reason", "Exclusion reason is not supported.")
        if reason.reason in seen_exclusion_reasons:
            add("duplicate_exclusion_reason", f"exclusion_reasons[{index}].reason", "Exclusion reasons must be unique.")
        seen_exclusion_reasons.add(reason.reason)
        if reason.examples == 0:
            add("empty_exclusion_reason", f"exclusion_reasons[{index}].examples", "Reported exclusion reasons must have a positive count.")
        if reason.examples > excluded:
            add("exclusion_count_exceeds_population", f"exclusion_reasons[{index}].examples", "An exclusion category cannot exceed excluded_records.")

    available_any = any(arm.available_output_population.examples > 0 for arm in report.arms.values())
    if report.evaluation_status == "evaluated" and (not ready or not available_any):
        add("evaluated_status_mismatch", "evaluation_status", "Evaluated status requires a ready dataset and at least one available output.")
    if report.evaluation_status == "no_metric_population" and available_any:
        add("no_metric_population_mismatch", "evaluation_status", "no_metric_population requires zero available outputs in both arms.")

    if report.matched_output_pairs == 0:
        for metric in ("bleu", "chrf"):
            if getattr(report.paired_aggregate_differences, metric) is not None:
                add("difference_without_pairs", f"paired_aggregate_differences.{metric}", "Paired differences must be null when there are no matched pairs.")
    else:
        for metric in ("bleu", "chrf"):
            direct = getattr(report.arms["direct"].matched_pair_population.scores, metric)
            assisted = getattr(report.arms["assisted"].matched_pair_population.scores, metric)
            difference = getattr(report.paired_aggregate_differences, metric)
            if direct is None or assisted is None or difference is None:
                add("missing_paired_metric", f"paired_aggregate_differences.{metric}", "Matched pairs require both arm scores and the assisted-minus-direct difference.")
            elif not _same(difference, assisted - direct):
                add("paired_difference_mismatch", f"paired_aggregate_differences.{metric}", "Paired difference must equal assisted matched-corpus score minus direct matched-corpus score.")

    if set(report.per_example_order_counts) != _METRICS:
        add("per_example_metric_keys", "per_example_order_counts", "Per-example metric keys must include BLEU and chrF.")
    for metric in sorted(_METRICS & set(report.per_example_order_counts)):
        counts = report.per_example_order_counts[metric]
        if set(counts) != {"higher", "lower", "equal", "denominator"}:
            add("per_example_count_keys", f"per_example_order_counts.{metric}", "Per-example relation counts have an invalid shape.")
            continue
        if any(count < 0 for count in counts.values()):
            add("negative_count", "per_example_order_counts" + _safe_location_part(metric), "Counts must be nonnegative integers.")
        if counts["denominator"] != report.matched_output_pairs or sum(counts[key] for key in ("higher", "lower", "equal")) != counts["denominator"]:
            add("per_example_denominator_mismatch", f"per_example_order_counts.{metric}", "Per-example order counts must partition the matched-pair population.")

    comparisons = report.per_example_comparisons
    comparison_ids = [item.example_id for item in comparisons]
    if len(comparison_ids) != len(set(comparison_ids)):
        add("duplicate_per_example_id", "per_example_comparisons", "Per-example comparison IDs must be unique.")
    if any(not item.example_id.strip() for item in comparisons):
        add("blank_per_example_id", "per_example_comparisons", "Per-example comparison IDs must be nonblank.")
    if comparisons and len(comparisons) != report.matched_output_pairs:
        add("partial_per_example_diagnostics", "per_example_comparisons", "When present, per-example comparisons must cover the complete matched population.")
    for index, item in enumerate(comparisons):
        for metric in ("bleu", "chrf"):
            direct = getattr(item, f"{metric}_direct")
            assisted = getattr(item, f"{metric}_assisted")
            difference = getattr(item, f"{metric}_assisted_minus_direct")
            path = f"per_example_comparisons[{index}]"
            if any(not (0.0 <= score <= 100.0) for score in (direct, assisted)):
                add("per_example_score_out_of_range", path, "Per-example metric scores must be within the evaluator's 0–100 scale.")
            if not _same(difference, assisted - direct):
                add("per_example_difference_mismatch", f"{path}.{metric}_assisted_minus_direct", "Per-example difference must equal assisted minus direct.")

    if comparisons and len(comparisons) == report.matched_output_pairs:
        for metric in sorted(_METRICS):
            observed = {"higher": 0, "lower": 0, "equal": 0}
            for item in comparisons:
                direct = getattr(item, f"{metric}_direct")
                assisted = getattr(item, f"{metric}_assisted")
                relation = "equal" if math.isclose(direct, assisted, abs_tol=1e-12) else (
                    "higher" if assisted > direct else "lower"
                )
                observed[relation] += 1
            stated = report.per_example_order_counts[metric]
            if any(observed[key] != stated[key] for key in observed):
                add("per_example_relation_mismatch", f"per_example_order_counts.{metric}", "Per-example relation counts must agree with the complete diagnostic listing.")

    human = report.human_semantic_preservation
    if set(human) != {"status", "reason"} or human.get("status") != "deferred" or not isinstance(human.get("reason"), str) or not human["reason"].strip():
        add("human_rating_claim_unsupported", "human_semantic_preservation", "This report contract supports only deferred human semantic-preservation scoring.")

    return errors


def validate_evaluation_report(value: object) -> EvaluationReportValidationResult:
    """Validate a parsed JSON value or existing report model without coercion."""
    if isinstance(value, EvaluationReport):
        raw: object = value.model_dump(mode="python")
    else:
        raw = value
    if not isinstance(raw, Mapping):
        return EvaluationReportValidationResult(
            status="INVALID",
            diagnostics=(_error("top_level_type", "$", "Evaluation report must be a JSON object."),),
        )
    if "schema_version" not in raw:
        return EvaluationReportValidationResult(
            status="INVALID",
            diagnostics=(_error("missing_schema_version", "schema_version", "Report schema_version is required."),),
        )
    version_result = _version_status(raw)
    if version_result is not None:
        return version_result
    if "metric_configuration" in raw and isinstance(raw["metric_configuration"], Mapping):
        for field_name in MetricConfiguration.model_fields:
            if field_name not in raw["metric_configuration"]:
                return EvaluationReportValidationResult(
                    status="INVALID",
                    diagnostics=(_error("missing_metric_configuration", f"metric_configuration.{field_name}", "Every supported metric setting must be explicit in a serialized report."),),
                )
    diagnostics = _finite_tree(raw)
    try:
        report = EvaluationReport.model_validate(raw, strict=True)
    except ValidationError as exc:
        for issue in exc.errors(include_input=False, include_context=False):
            location = "$" + "".join(_safe_location_part(part) for part in issue["loc"])
            code = "schema_" + str(issue["type"])
            diagnostics.append(_error(code, location, f"Invalid report value ({issue['type']})."))
        return EvaluationReportValidationResult(status="INVALID", diagnostics=tuple(sorted(diagnostics, key=lambda item: (item.location, item.code, item.message))))

    diagnostics.extend(_integrity_errors(report))
    unique = {(item.code, item.location, item.message): item for item in diagnostics}
    ordered = tuple(unique[key] for key in sorted(unique))
    return EvaluationReportValidationResult(status="INVALID" if ordered else "VALID", diagnostics=ordered)
