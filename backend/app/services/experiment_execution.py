"""Eligibility-gated, versioned JSONL experiment execution."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from app.schemas.evaluation import PairedEvaluationArtifact
from app.schemas.experiment import ExperimentConfiguration
from app.services.dataset_validation import _unique_object_pairs, validate_dataset
from app.services.evaluation_readiness import check_evaluation_readiness
from app.services.experiment import run_paired_experiment
from app.services.translation import TranslationProvider


class ExperimentExecutionError(ValueError):
    pass


def run_dataset_experiment(
    annotations: str | Path,
    output: str | Path,
    *,
    split: Literal["train", "validation", "test"],
    provider: TranslationProvider | None,
    configuration: ExperimentConfiguration | None = None,
    allow_provider_calls: bool = False,
) -> Path:
    """Run only a ready dataset; require an explicit caller opt-in for calls.

    The output is one canonical PairedEvaluationArtifact v1.0 JSON object per
    selected example. Creation is exclusive: an existing path is never replaced.
    """
    source, destination = Path(annotations), Path(output)
    if source.resolve() == destination.resolve():
        raise ExperimentExecutionError("output must not overwrite the annotation dataset")
    if not destination.parent.is_dir():
        raise ExperimentExecutionError("output directory does not exist")
    if destination.exists():
        raise ExperimentExecutionError("output artifact already exists")
    if provider is None:
        raise ExperimentExecutionError("a translation provider must be configured")
    if allow_provider_calls is not True:
        raise ExperimentExecutionError("provider calls require explicit allow_provider_calls=True")

    structural = validate_dataset(source)
    if structural.errors:
        raise ExperimentExecutionError("annotation structural validation failed")
    readiness = check_evaluation_readiness(source)
    if not readiness.ready:
        raise ExperimentExecutionError("annotation dataset is not eligible for evaluation")

    rows = []
    try:
        with source.open(encoding="utf-8") as stream:
            for line_number, raw in enumerate(stream, start=1):
                if not raw.strip():
                    continue
                row = json.loads(raw, object_pairs_hook=_unique_object_pairs)
                if row.get("split") == split:
                    rows.append((line_number, row))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        raise ExperimentExecutionError("annotation dataset could not be read safely") from None
    if not rows:
        raise ExperimentExecutionError("requested split contains no examples")

    config = configuration or ExperimentConfiguration()
    artifacts = []
    for _line, row in rows:
        result = run_paired_experiment(row["text"], provider=provider, configuration=config)
        artifacts.append(PairedEvaluationArtifact(
            schema_version="1.0", example_id=row["id"], split=split, result=result,
        ))

    payload = "".join(
        json.dumps(item.model_dump(mode="json"), ensure_ascii=False, sort_keys=True,
                   separators=(",", ":")) + "\n"
        for item in artifacts
    )
    try:
        with destination.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
    except FileExistsError:
        raise ExperimentExecutionError("output artifact already exists") from None
    except OSError:
        raise ExperimentExecutionError("output artifact could not be created") from None
    return destination
