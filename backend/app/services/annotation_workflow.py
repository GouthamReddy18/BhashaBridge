"""Safe offline helpers for preparing annotation drafts and dataset releases."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.services.dataset_validation import validate_dataset
from app.services.evaluation_readiness import check_evaluation_readiness
from app.services.language_identification import RuleBasedTokenLanguageIdentifier
from app.services.preprocessing import normalize_whitespace
from app.services.tokenization import tokenize


class WorkflowError(ValueError):
    """A requested workflow operation cannot be completed safely."""


def _record_bytes(path: str | Path) -> bytes:
    try:
        return Path(path).read_bytes()
    except OSError as exc:
        raise WorkflowError(f"cannot read {path}: {exc}") from exc


def _write_new(path: str | Path, payload: bytes) -> Path:
    """Create a new file only; never follow/replace an existing destination."""
    destination = Path(path)
    if not destination.parent.is_dir():
        raise WorkflowError(f"output directory does not exist: {destination.parent}")
    try:
        stream = destination.open("xb")
    except FileExistsError as exc:
        raise WorkflowError(f"output already exists: {destination}") from exc
    except OSError as exc:
        raise WorkflowError(f"cannot create {destination}: {exc}") from exc
    try:
        with stream:
            stream.write(payload)
            stream.flush()
    except OSError as exc:
        # Remove only the file this call successfully created, if writing failed.
        try:
            destination.unlink()
        except OSError:
            pass
        raise WorkflowError(f"cannot create {destination}: {exc}") from exc
    return destination


def create_draft(
    output: str | Path,
    *,
    record_id: str,
    text: str,
    source_type: str,
    source_details: str,
) -> Path:
    """Write a single schema-shaped draft with baseline labels, never review claims."""
    for field, value in (("id", record_id), ("text", text), ("source_type", source_type), ("source_details", source_details)):
        if not isinstance(value, str) or not value.strip():
            raise WorkflowError(f"{field} must be a nonblank string")
    normalized = normalize_whitespace(text)
    if not normalized:
        raise WorkflowError("text must contain a non-whitespace character")
    tokens = tokenize(normalized)
    labels = RuleBasedTokenLanguageIdentifier().identify(tokens)
    record: dict[str, Any] = {
        "annotation_version": "1.0",
        "id": record_id,
        "text": text,
        "normalized_text": normalized,
        "source_type": source_type,
        "annotation_status": "draft",
        "annotation_provenance": {
            "method": "annotation_workflow_draft_scaffold",
            "details": source_details,
            "origin": "machine",
        },
        "tokens": [
            {
                "index": index,
                "surface": token.text,
                "start": token.start,
                "end": token.end,
                "language_label": annotation.label,
            }
            for index, (token, annotation) in enumerate(zip(tokens, labels))
        ],
        "romanized_interpretation": None,
        "telugu_script_equivalent": None,
        "ambiguity": None,
        "reference_translation": None,
        "intended_meaning": None,
        "annotation_notes": "Draft scaffold; verify every label and add sourced annotations. No human review is claimed.",
        "review": {"status": "not_reviewed"},
    }
    payload = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    destination = _write_new(output, payload)
    report = validate_dataset(destination)
    if not report.valid:
        destination.unlink(missing_ok=True)
        raise WorkflowError("generated draft failed structural validation: " + "; ".join(issue.message for issue in report.errors))
    return destination


def export_ready_dataset(source: str | Path, output: str | Path) -> Path:
    """Copy a whole eligible dataset to a new immutable output path."""
    source_path, output_path = Path(source), Path(output)
    try:
        if source_path.resolve() == output_path.resolve():
            raise WorkflowError("source and output paths must differ")
    except OSError as exc:
        raise WorkflowError(f"cannot resolve dataset paths: {exc}") from exc
    before = _record_bytes(source_path)
    readiness = check_evaluation_readiness(source_path)
    if not readiness.ready:
        raise WorkflowError(f"dataset is not evaluation-ready ({len(readiness.errors)} error(s)); no export written")
    after = _record_bytes(source_path)
    if before != after:
        raise WorkflowError("dataset changed during readiness check; no export written")
    return _write_new(output_path, after)


def _read_objects(path: str | Path) -> tuple[bytes, dict[str, dict[str, Any]]]:
    raw = _record_bytes(path)
    objects: dict[str, dict[str, Any]] = {}
    try:
        for line_number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict) or not isinstance(value.get("id"), str):
                raise WorkflowError(f"{path}:{line_number} must be an object with a string id")
            if value["id"] in objects:
                raise WorkflowError(f"{path}:{line_number} repeats record id {value['id']!r}")
            objects[value["id"]] = value
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"cannot parse JSONL {path}: {exc}") from exc
    return raw, objects


def write_revision_manifest(
    original: str | Path,
    revised: str | Path,
    output: str | Path,
    *,
    change_note: str,
) -> Path:
    """Record a deterministic hash-linked revision after a human edits a copy."""
    if not isinstance(change_note, str) or not change_note.strip():
        raise WorkflowError("change_note must be a nonblank string")
    try:
        if Path(output).resolve() in {Path(original).resolve(), Path(revised).resolve()}:
            raise WorkflowError("revision manifest must not replace either dataset")
    except OSError as exc:
        raise WorkflowError(f"cannot resolve revision paths: {exc}") from exc
    for path in (original, revised):
        report = validate_dataset(path)
        if not report.valid:
            raise WorkflowError(f"{path} is structurally invalid ({len(report.errors)} error(s)); revision not recorded")
    old_bytes, old_records = _read_objects(original)
    new_bytes, new_records = _read_objects(revised)
    for path, expected in ((original, old_bytes), (revised, new_bytes)):
        if _record_bytes(path) != expected:
            raise WorkflowError(f"{path} changed during revision validation")
    if old_records.keys() != new_records.keys():
        raise WorkflowError("revision must preserve the set of record IDs")
    changed = sorted(record_id for record_id in old_records if old_records[record_id] != new_records[record_id])
    if not changed:
        raise WorkflowError("revised dataset contains no record changes")
    manifest = {
        "manifest_version": "1.0",
        "source_sha256": hashlib.sha256(old_bytes).hexdigest(),
        "revised_sha256": hashlib.sha256(new_bytes).hexdigest(),
        "changed_record_ids": changed,
        "change_note": change_note.strip(),
    }
    identity = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest["revision_id"] = hashlib.sha256(identity).hexdigest()
    payload = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    return _write_new(output, payload)
