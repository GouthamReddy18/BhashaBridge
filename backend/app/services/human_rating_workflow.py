"""Pending human-rating task preparation and descriptive aggregation."""
from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import ValidationError

from app.schemas.evaluation import PairedEvaluationArtifact
from app.schemas.human_rating import HumanRatingRecord
from app.services.dataset_validation import _unique_object_pairs, validate_dataset
from app.services.evaluation_readiness import check_evaluation_readiness
from app.services.google_translation import PROVIDER_ID as RESEARCH_PROVIDER_ID

RUBRIC_VERSION = "semantic-preservation-0-4.v1"
_SAFE_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,79}$")


class RatingWorkflowError(ValueError):
    pass


def _read_jsonl(path):
    try:
        with Path(path).open(encoding="utf-8-sig") as stream:
            return [json.loads(line, object_pairs_hook=_unique_object_pairs) for line in stream if line.strip()]
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        raise RatingWorkflowError("rating workflow input could not be read safely") from None


def _write_new(path, payload):
    path = Path(path)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
    except FileExistsError:
        raise RatingWorkflowError("rating output already exists") from None
    except OSError:
        raise RatingWorkflowError("rating output could not be created") from None
    return path


def create_rating_tasks(annotations, paired_results, *, split, tasks_output, ratings_output,
                       blinded=False, mapping_output=None, dataset_label="unlabeled"):
    """Write rater stimuli plus explicitly pending rows; never create ratings."""
    if split not in {"train", "validation", "test"}:
        raise RatingWorkflowError("unsupported split")
    if blinded != (mapping_output is not None):
        raise RatingWorkflowError("blinded tasks require a separate mapping output")
    if not isinstance(dataset_label, str) or not _SAFE_LABEL.fullmatch(dataset_label) or re.search(r"(?:api.?key|secret|token|password|^sk-)", dataset_label, re.IGNORECASE):
        raise RatingWorkflowError("dataset_label must be a short safe label")
    sources = {Path(annotations).resolve(), Path(paired_results).resolve()}
    outputs = [Path(tasks_output), Path(ratings_output)]
    if mapping_output is not None:
        outputs.append(Path(mapping_output))
    resolved = [path.resolve() for path in outputs]
    if len(resolved) != len(set(resolved)) or any(path in sources for path in resolved):
        raise RatingWorkflowError("rating outputs must be distinct and must not overwrite inputs")
    if any(path.exists() for path in outputs):
        raise RatingWorkflowError("rating output already exists")
    if any(not path.parent.is_dir() for path in outputs):
        raise RatingWorkflowError("output directory does not exist")
    if validate_dataset(annotations).errors:
        raise RatingWorkflowError("annotation structural validation failed")
    if not check_evaluation_readiness(annotations).ready:
        raise RatingWorkflowError("annotation dataset is not eligible for human rating")
    annotation_rows = [row for row in _read_jsonl(annotations) if row.get("split") == split]
    if not annotation_rows:
        raise RatingWorkflowError("requested split contains no examples")
    annotation_by_id = {row["id"]: row for row in annotation_rows}
    artifacts = {}
    for raw in _read_jsonl(paired_results):
        try:
            artifact = PairedEvaluationArtifact.model_validate(raw)
        except ValidationError:
            raise RatingWorkflowError("paired artifact schema is invalid") from None
        if artifact.example_id in artifacts:
            raise RatingWorkflowError("paired artifact IDs must be unique")
        artifacts[artifact.example_id] = artifact

    tasks, ratings, mapping = [], [], []
    for example_id, row in sorted(annotation_by_id.items()):
        artifact = artifacts.get(example_id)
        if artifact:
            if artifact.split is not None and artifact.split != split:
                raise RatingWorkflowError("paired artifact split conflicts with annotation")
            if artifact.result.original_input != row["text"]:
                raise RatingWorkflowError("paired artifact source conflicts with annotation")
            if any(
                (outcome := getattr(artifact.result, arm).translation).status == "success"
                and outcome.provider_id != RESEARCH_PROVIDER_ID
                for arm in ("direct", "assisted")
            ):
                raise RatingWorkflowError("unregistered provider outputs cannot enter human-rating tasks")
        arms = ["direct", "assisted"]
        labels = {"direct": "direct", "assisted": "assisted"}
        if blinded:
            import secrets
            if secrets.randbelow(2):
                arms.reverse()
            labels = {arms[0]: "A", arms[1]: "B"}
        items = []
        for arm in arms:
            outcome = getattr(artifact.result, arm).translation if artifact else None
            text = outcome.translated_text if outcome and outcome.status == "success" else None
            label = labels[arm]
            items.append({"display_label": label, "translation_text": text,
                          "translation_status": outcome.status if outcome else "missing"})
            ratings.append(HumanRatingRecord(
                schema_version="1.0", rubric_version=RUBRIC_VERSION, example_id=example_id,
                arm=None if blinded else arm, display_label=label if blinded else None,
            ).model_dump(mode="json"))
            if blinded:
                mapping.append({"example_id": example_id, "display_label": label, "arm": arm})
        tasks.append({"schema_version": "1.0", "rubric_version": RUBRIC_VERSION,
                      "dataset_label": dataset_label, "split": split,
                      "example_id": example_id, "source_text": row["text"],
                      "intended_meaning": row["intended_meaning"], "blinded": blinded, "items": items})

    _write_new(tasks_output, "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in tasks))
    _write_new(ratings_output, "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in ratings))
    if mapping_output is not None:
        _write_new(mapping_output, json.dumps({"schema_version": "1.0", "mapping": mapping},
                                              ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return Path(tasks_output), Path(ratings_output), Path(mapping_output) if mapping_output else None


def aggregate_human_ratings(tasks_path, ratings_path, *, mapping_path=None, min_reviewers=1):
    """Summarize complete ratings only, with per-arm coverage and missingness."""
    if isinstance(min_reviewers, bool) or not isinstance(min_reviewers, int) or min_reviewers < 1:
        raise RatingWorkflowError("min_reviewers must be a positive integer")
    tasks = _read_jsonl(tasks_path)
    expected = {}
    blinded = False
    task_labels, task_splits = set(), set()
    for task in tasks:
        example_id = task.get("example_id")
        if (task.get("schema_version") != "1.0" or task.get("rubric_version") != RUBRIC_VERSION
                or not isinstance(example_id, str) or not example_id.strip()
                or not isinstance(task.get("blinded"), bool)):
            raise RatingWorkflowError("rating task schema is invalid")
        blinded = blinded or task.get("blinded") is True
        if task.get("dataset_label") is not None:
            if not isinstance(task["dataset_label"], str) or not _SAFE_LABEL.fullmatch(task["dataset_label"]):
                raise RatingWorkflowError("rating task dataset label is invalid")
            task_labels.add(task["dataset_label"])
        if task.get("split") is not None:
            if task["split"] not in {"train", "validation", "test"}:
                raise RatingWorkflowError("rating task split is invalid")
            task_splits.add(task["split"])
        items = task.get("items")
        if not isinstance(items, list) or len(items) != 2 or any(not isinstance(item, dict) for item in items):
            raise RatingWorkflowError("each task must contain two arms")
        labels = {item.get("display_label") for item in items}
        if labels != ({"A", "B"} if task.get("blinded") else {"direct", "assisted"}):
            raise RatingWorkflowError("task arm labels are invalid")
        for item in items:
            if item.get("translation_text") is not None and not isinstance(item.get("translation_text"), str):
                raise RatingWorkflowError("task translation text is invalid")
            expected[(example_id, item["display_label"])] = item.get("translation_text") is not None
    if not tasks or len({task.get("example_id") for task in tasks}) != len(tasks):
        raise RatingWorkflowError("tasks must contain unique examples")
    if len(task_labels) > 1 or len(task_splits) > 1:
        raise RatingWorkflowError("rating tasks must use one dataset label and split")
    if task_labels and (not _SAFE_LABEL.fullmatch(next(iter(task_labels)))):
        raise RatingWorkflowError("rating task dataset label is invalid")
    if task_splits and next(iter(task_splits)) not in {"train", "validation", "test"}:
        raise RatingWorkflowError("rating task split is invalid")

    arm_map = {}
    if blinded:
        if mapping_path is None:
            raise RatingWorkflowError("blinded aggregation requires the separate mapping file")
        try:
            mapping = json.loads(Path(mapping_path).read_text(encoding="utf-8-sig"))
            if mapping.get("schema_version") != "1.0":
                raise ValueError
            for item in mapping["mapping"]:
                key = (item["example_id"], item["display_label"])
                if key in arm_map or item["arm"] not in {"direct", "assisted"}:
                    raise ValueError
                arm_map[key] = item["arm"]
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError, AttributeError):
            raise RatingWorkflowError("blinded mapping is invalid") from None
        if set(arm_map) != set(expected):
            raise RatingWorkflowError("blinded mapping is incomplete")
        for task in tasks:
            if {arm_map[(task["example_id"], label)] for label in ("A", "B")} != {"direct", "assisted"}:
                raise RatingWorkflowError("blinded mapping contradicts task labels")

    records, seen = [], set()
    for raw in _read_jsonl(ratings_path):
        try:
            rating = HumanRatingRecord.model_validate(raw)
        except ValidationError:
            raise RatingWorkflowError("human rating record schema is invalid") from None
        label = rating.arm or rating.display_label
        key = (rating.example_id, label)
        if key not in expected:
            raise RatingWorkflowError("rating refers to an unexpected example or arm")
        if rating.status == "complete" and not expected[key]:
            raise RatingWorkflowError("a missing or failed translation cannot have a completed rating")
        arm = arm_map[key] if blinded else label
        identity = (rating.example_id, arm, rating.reviewer_id)
        if identity in seen:
            raise RatingWorkflowError("duplicate reviewer judgment for an example and arm")
        seen.add(identity)
        records.append((rating, arm, expected[key]))

    report = {"schema_version": "1.0", "rubric_version": RUBRIC_VERSION,
              "minimum_independent_reviewers": min_reviewers, "blinded_presentation": blinded,
              "dataset_label": next(iter(task_labels)) if task_labels else None,
              "split": next(iter(task_splits)) if task_splits else None,
              "arms": {}, "inter_annotator_agreement": {
                  "status": "not_calculated", "reason": "No agreement statistic is implemented."}}
    for arm in ("direct", "assisted"):
        per_example, pending, available, unavailable = {}, 0, 0, 0
        available_ids, unavailable_ids = [], []
        for (example_id, label), has_output in expected.items():
            resolved_arm = arm_map[(example_id, label)] if blinded else label
            if resolved_arm == arm:
                available += int(has_output)
                unavailable += int(not has_output)
                (available_ids if has_output else unavailable_ids).append(example_id)
        for rating, resolved_arm, has_output in records:
            if resolved_arm != arm:
                continue
            if rating.status == "pending" and has_output:
                pending += 1
            elif has_output:
                per_example.setdefault(rating.example_id, []).append(rating.rating)
        included = sorted(key for key, scores in per_example.items() if len(scores) >= min_reviewers)
        included_scores = [score for key in included for score in per_example[key]]
        report["arms"][arm] = {
            "available_output_examples": available,
            "available_output_example_ids": sorted(available_ids),
            "unavailable_output_example_ids": sorted(unavailable_ids),
            "unavailable_output_examples": unavailable,
            "rated_examples_with_required_reviewers": len(included),
            "rated_example_ids": included,
            "missing_or_insufficiently_reviewed_examples": max(0, available - len(included)),
            "pending_judgments": pending,
            "completed_judgments": len(included_scores),
            "rating_distribution": {
                str(score): sum(item == score for item in included_scores)
                for score in range(5)
            },
        }
    report["warnings"] = [
        "Reviewer provenance is supplied metadata and is not authenticated.",
        "Human scores are descriptive ordinal summaries; BLEU/chrF are not used to infer ratings.",
    ]
    return report
