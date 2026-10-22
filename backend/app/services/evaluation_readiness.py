"""Read-only eligibility checks for future paired translation evaluation."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.services.dataset_validation import (
    ValidationIssue,
    _unique_object_pairs,
    validate_dataset,
)

HUMAN_ORIGINS = {"human", "human_and_machine"}
SPLITS = {"train", "validation", "test"}


@dataclass
class EvaluationReadinessReport:
    path: str
    records_examined: int
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not self.errors and self.records_examined > 0


def _add(issues: list[ValidationIssue], line: int, message: str, record_id: str | None) -> None:
    issues.append(ValidationIssue(line=line, message=message, record_id=record_id))


def _human_reviewed_field(record: dict[str, Any], name: str) -> bool:
    provenance = record.get("annotation_provenance")
    fields = provenance.get("fields") if isinstance(provenance, dict) else None
    field_info = fields.get(name) if isinstance(fields, dict) else None
    return (
        isinstance(field_info, dict)
        and isinstance(field_info.get("origin"), str)
        and field_info.get("origin") in HUMAN_ORIGINS
        and field_info.get("review_status") == "reviewed"
        and isinstance(field_info.get("details"), str)
        and bool(field_info["details"].strip())
        and isinstance(field_info.get("source_reference"), str)
        and bool(field_info["source_reference"].strip())
    )


def check_evaluation_readiness(path: str | Path) -> EvaluationReadinessReport:
    """Check structure and benchmark metadata without changing the JSONL source."""
    source = Path(path)
    structural = validate_dataset(source)
    errors = list(structural.errors)
    warnings = list(structural.warnings)
    report = EvaluationReadinessReport(
        path=str(source),
        records_examined=structural.records_examined,
        errors=errors,
        warnings=warnings,
    )

    if structural.records_examined == 0:
        unreadable = any(
            issue.line == 0 and issue.message.startswith("cannot read dataset:")
            for issue in structural.errors
        )
        if not unreadable:
            _add(errors, 0, "dataset contains no records", None)
        return report

    rows: list[tuple[int, dict[str, Any]]] = []
    try:
        with source.open(encoding="utf-8") as stream:
            for line, raw in enumerate(stream, start=1):
                if not raw.strip():
                    continue
                try:
                    value = json.loads(raw, object_pairs_hook=_unique_object_pairs)
                except (json.JSONDecodeError, ValueError):
                    continue  # Structural validation already reports this line.
                if isinstance(value, dict):
                    rows.append((line, value))
    except (OSError, UnicodeError):
        return report  # The structural validator already reported the read error.

    split_groups: dict[str, tuple[str, int, str | None]] = {}
    normalized_sources: dict[str, tuple[str, int, str | None]] = {}
    for line, record in rows:
        rid = record.get("id") if isinstance(record.get("id"), str) else None
        if record.get("annotation_status") != "reviewed":
            _add(errors, line, "record is not reviewed and is ineligible for benchmark use", rid)
        review = record.get("review")
        if not isinstance(review, dict) or review.get("status") != "reviewed":
            _add(errors, line, "completed review metadata is required", rid)

        provenance = record.get("annotation_provenance")
        if (
            not isinstance(provenance, dict)
            or not isinstance(provenance.get("origin"), str)
            or provenance.get("origin") not in HUMAN_ORIGINS
        ):
            _add(errors, line, "benchmark provenance must include a human contribution", rid)

        reference = record.get("reference_translation")
        if not isinstance(reference, str) or not reference.strip():
            _add(errors, line, "human-reviewed English reference_translation is required", rid)
        if not _human_reviewed_field(record, "reference_translation"):
            _add(errors, line, "reference_translation requires reviewed human provenance and source_reference", rid)

        meaning = record.get("intended_meaning")
        if not isinstance(meaning, str) or not meaning.strip():
            _add(errors, line, "reviewed intended_meaning is required for semantic assessment", rid)
        if not _human_reviewed_field(record, "intended_meaning"):
            _add(errors, line, "intended_meaning requires reviewed human provenance and source_reference", rid)

        split = record.get("split")
        if not isinstance(split, str) or split not in SPLITS:
            _add(errors, line, "a valid split assignment (train, validation, or test) is required", rid)
        group = record.get("split_group")
        if not isinstance(group, str) or not group.strip():
            _add(errors, line, "split_group is required for group-aware leakage control", rid)
        elif isinstance(split, str) and split in SPLITS:
            previous = split_groups.get(group)
            if previous and previous[0] != split:
                _add(errors, line, f"split_group {group!r} crosses splits; first seen on line {previous[1]} (record {previous[2]})", rid)
            else:
                split_groups.setdefault(group, (split, line, rid))

        if split == "test":
            tokens = record.get("tokens")
            labels = {
                token.get("language_label")
                for token in tokens
                if isinstance(token, dict)
                and isinstance(token.get("language_label"), str)
            } if isinstance(tokens, list) else set()
            if not {"TELUGU_ROMANIZED", "ENGLISH"}.issubset(labels):
                _add(errors, line, "test examples must contain both TELUGU_ROMANIZED and ENGLISH tokens", rid)

        normalized = record.get("normalized_text")
        if isinstance(normalized, str) and isinstance(split, str) and split in SPLITS:
            previous = normalized_sources.get(normalized)
            if previous and previous[0] != split:
                _add(errors, line, f"exact normalized source text crosses splits; first seen on line {previous[1]} (record {previous[2]})", rid)
            elif previous:
                _add(errors, line, f"duplicate normalized source text within split {split!r}; first seen on line {previous[1]} (record {previous[2]})", rid)
            else:
                normalized_sources.setdefault(normalized, (split, line, rid))

    return report
