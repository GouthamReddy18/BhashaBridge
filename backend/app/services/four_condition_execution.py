"""Readiness-gated deterministic JSONL execution for four conditions."""
from __future__ import annotations

import json
from pathlib import Path

from app.schemas.four_condition import FourConditionConfiguration
from app.services.dataset_validation import _unique_object_pairs, validate_dataset
from app.services.evaluation_readiness import check_evaluation_readiness
from app.services.four_condition_experiment import (
    FourConditionExecutionError, run_four_condition_experiment,
)
from app.services.translation import TranslationProvider


class FourConditionDatasetError(ValueError):
    pass


def run_four_condition_dataset(
    annotations: str | Path,
    output: str | Path,
    *,
    configuration: FourConditionConfiguration,
    provider: TranslationProvider | None,
    allow_provider_calls: bool = False,
    allow_test_fixtures: bool = False,
) -> Path:
    source, destination = Path(annotations), Path(output)
    if source.resolve() == destination.resolve():
        raise FourConditionDatasetError("output must not overwrite the annotation dataset")
    if not destination.parent.is_dir():
        raise FourConditionDatasetError("output directory does not exist")
    if destination.exists():
        raise FourConditionDatasetError("output artifact already exists")
    if provider is not None and allow_provider_calls is not True:
        raise FourConditionDatasetError("provider calls require explicit authorization")

    structural = validate_dataset(source)
    if structural.errors:
        raise FourConditionDatasetError("annotation structural validation failed")
    readiness = check_evaluation_readiness(source)
    if not readiness.ready and not allow_test_fixtures:
        raise FourConditionDatasetError("annotation dataset is not eligible for research execution")
    rows: list[dict] = []
    try:
        with source.open(encoding="utf-8") as stream:
            for raw in stream:
                if not raw.strip():
                    continue
                row = json.loads(raw, object_pairs_hook=_unique_object_pairs)
                if row.get("split") == configuration.split:
                    rows.append(row)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        raise FourConditionDatasetError("annotation dataset could not be read safely") from None
    if not rows:
        raise FourConditionDatasetError("requested split contains no examples")
    rows.sort(key=lambda item: item["id"])

    artifacts = []
    try:
        for row in rows:
            artifacts.append(run_four_condition_experiment(
                row["id"], row["text"], configuration=configuration,
                provider=provider, allow_provider_calls=allow_provider_calls,
                allow_test_fixtures=allow_test_fixtures,
            ))
    except FourConditionExecutionError as exc:
        raise FourConditionDatasetError(str(exc)) from None
    payload = "".join(
        json.dumps(artifact.model_dump(mode="json"), ensure_ascii=False,
                   sort_keys=True, separators=(",", ":")) + "\n"
        for artifact in artifacts
    )
    try:
        with destination.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
    except FileExistsError:
        raise FourConditionDatasetError("output artifact already exists") from None
    except OSError:
        raise FourConditionDatasetError("output artifact could not be created") from None
    return destination
