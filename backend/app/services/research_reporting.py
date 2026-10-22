"""Validated descriptive research-report composition; no inferential statistics."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.dataset_validation import _unique_object_pairs
from app.services.evaluation_report_validation import validate_evaluation_report


class ResearchReportError(ValueError):
    pass


def _read_json(path: str | Path) -> Any:
    try:
        with Path(path).open(encoding="utf-8-sig") as stream:
            return json.load(stream, object_pairs_hook=_unique_object_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        raise ResearchReportError("report input could not be read safely") from None


def _check_human_summary(value: object, *, evaluation: dict) -> dict:
    if not isinstance(value, dict) or value.get("schema_version") != "1.0":
        raise ResearchReportError("human-rating summary schema is invalid")
    if value.get("rubric_version") != "semantic-preservation-0-4.v1":
        raise ResearchReportError("human-rating rubric version is unsupported")
    if value.get("dataset_label") != evaluation["dataset_label"] or value.get("split") != evaluation["split"]:
        raise ResearchReportError("human-rating summary dataset/split does not match evaluation report")
    minimum = value.get("minimum_independent_reviewers")
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
        raise ResearchReportError("human-rating reviewer threshold is invalid")
    if not isinstance(value.get("blinded_presentation"), bool):
        raise ResearchReportError("human-rating blinded-presentation metadata is invalid")
    arms = value.get("arms")
    if not isinstance(arms, dict) or set(arms) != {"direct", "assisted"}:
        raise ResearchReportError("human-rating arm summaries are invalid")
    if not isinstance(evaluation.get("eligible_example_ids"), list) or any(
        not isinstance(evaluation["arms"][name].get("available_output_example_ids"), list)
        for name in ("direct", "assisted")
    ):
        raise ResearchReportError("evaluation report lacks IDs required to link human ratings safely")
    for arm_name in ("direct", "assisted"):
        arm = arms[arm_name]
        if not isinstance(arm, dict):
            raise ResearchReportError("human-rating arm summary is invalid")
        evaluation_arm = evaluation["arms"][arm_name]
        available_ids = arm.get("available_output_example_ids")
        unavailable_ids = arm.get("unavailable_output_example_ids")
        rated_ids = arm.get("rated_example_ids")
        for name, ids in (("available", available_ids), ("unavailable", unavailable_ids), ("rated", rated_ids)):
            if not isinstance(ids, list) or any(not isinstance(item, str) for item in ids) or ids != sorted(set(ids)):
                raise ResearchReportError(f"human-rating {name} IDs are invalid")
        if available_ids != evaluation_arm["available_output_example_ids"]:
            raise ResearchReportError("human-rating available IDs do not match evaluated arm outputs")
        eligible_ids = set(evaluation.get("eligible_example_ids", []))
        if set(available_ids) & set(unavailable_ids) or set(available_ids) | set(unavailable_ids) != eligible_ids:
            raise ResearchReportError("human-rating output availability does not cover the eligible IDs")
        if not set(rated_ids).issubset(set(available_ids)):
            raise ResearchReportError("human-rated IDs must have an available arm output")
        counters = {
            "available_output_examples": len(available_ids),
            "unavailable_output_examples": len(unavailable_ids),
            "rated_examples_with_required_reviewers": len(rated_ids),
            "missing_or_insufficiently_reviewed_examples": len(available_ids) - len(rated_ids),
        }
        for field, expected in counters.items():
            count = arm.get(field)
            if isinstance(count, bool) or not isinstance(count, int) or count != expected:
                raise ResearchReportError(f"human-rating {field} does not reconcile")
        pending = arm.get("pending_judgments")
        if isinstance(pending, bool) or not isinstance(pending, int) or pending < 0:
            raise ResearchReportError("human-rating pending count is invalid")
        distribution = arm.get("rating_distribution")
        if not isinstance(distribution, dict) or set(distribution) != {str(score) for score in range(5)}:
            raise ResearchReportError("human-rating distribution must include scores 0 through 4")
        values = list(distribution.values())
        if any(isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in values):
            raise ResearchReportError("human-rating distribution counts are invalid")
        completed = arm.get("completed_judgments")
        if isinstance(completed, bool) or not isinstance(completed, int) or completed != sum(values):
            raise ResearchReportError("human-rating distribution does not match completed judgments")
        if completed < len(rated_ids) * minimum:
            raise ResearchReportError("human-rating reviewer threshold does not reconcile")
    agreement = value.get("inter_annotator_agreement")
    if not isinstance(agreement, dict) or agreement.get("status") != "not_calculated":
        raise ResearchReportError("unsupported inter-rater agreement claims are rejected")
    return value


def build_research_report(evaluation: object, human_ratings: object | None = None) -> dict[str, Any]:
    """Validate and compose descriptive artifacts with explicit inference limits."""
    validation = validate_evaluation_report(evaluation)
    if validation.status != "VALID":
        raise ResearchReportError("evaluation report failed integrity validation")
    if not isinstance(evaluation, dict):
        evaluation = evaluation.model_dump(mode="json")
    if evaluation.get("eligible_records", 0) <= 0:
        raise ResearchReportError("evaluation report contains no eligible records")
    if evaluation.get("evaluation_status") == "not_evaluated":
        raise ResearchReportError("evaluation readiness blocked this report")
    ratings = _check_human_summary(human_ratings, evaluation=evaluation) if human_ratings is not None else None
    limitations = [
        "Reference-based BLEU and chrF are descriptive proxies, not direct semantic-preservation measurements.",
        "No statistical significance test, confidence interval, or causal claim is produced.",
        "Report validity does not authenticate annotation provenance, provider outputs, or reviewer identity.",
        "Provider failures, missing outputs, exclusions, and assisted-input categories remain part of interpretation.",
    ]
    if ratings is None:
        limitations.append("No human semantic-preservation rating summary was supplied; no human score is available.")
    else:
        limitations.append("Human rating distributions are ordinal and descriptive; no agreement statistic is calculated.")
    return {
        "schema_version": "1.0",
        "report_status": "descriptive_metrics_available" if evaluation["evaluation_status"] == "evaluated" else "eligible_no_metric_population",
        "evaluation_validation_status": validation.status,
        "evaluation_report": evaluation,
        "human_rating_summary": ratings,
        "limitations": limitations,
    }


def build_research_report_file(evaluation_path, output_path, *, human_ratings_path=None) -> Path:
    source = Path(evaluation_path).resolve()
    destination = Path(output_path)
    if destination.resolve() == source or (
        human_ratings_path is not None and destination.resolve() == Path(human_ratings_path).resolve()
    ):
        raise ResearchReportError("output must not overwrite an input report")
    if not destination.parent.is_dir():
        raise ResearchReportError("output directory does not exist")
    if destination.exists():
        raise ResearchReportError("output already exists")
    evaluation = _read_json(source)
    human = _read_json(human_ratings_path) if human_ratings_path is not None else None
    report = build_research_report(evaluation, human)
    try:
        with destination.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
    except FileExistsError:
        raise ResearchReportError("output already exists") from None
    except OSError:
        raise ResearchReportError("research report could not be written safely") from None
    return destination
