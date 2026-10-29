"""
BhashaBridge — Offline annotation-import service (Phase 29).

Accepts a completed reviewer CSV file, validates every declared field, and
produces a new merged JSONL that embeds the reviewer's annotations into the
original pilot draft records.

Safeguards (none weaken existing readiness rules):
- Only known pilot record IDs are accepted.
- Source text must not change.
- Required reviewer-metadata fields must be present and non-blank.
- Missing or blank reference translations are rejected.
- Missing or blank intended meanings are rejected.
- Duplicate IDs in the submission are rejected.
- Accidental source-text changes are rejected.
- Unsupported annotation_status transitions are rejected.
- Existing reviewed records are never silently overwritten.
- Author-proposed draft notes are preserved alongside reviewer content.
- The importer cannot authenticate that a person performed the review;
  that distinction is documented and left to the external audit trail.
- No record in the merged output is automatically promoted to 'reviewed'.
  That must be done explicitly by the human reviewer after the merged JSONL
  passes structural validation.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.services.dataset_validation import validate_dataset
from app.services.preprocessing import normalize_whitespace

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

REQUIRED_REVIEWER_FIELDS = {
    "reviewer_id",
    "language_competency_declaration",
    "guideline_version",
    "saw_system_outputs",
    "independence_declaration",
}

REQUIRED_PER_ROW_FIELDS = {
    "example_id",
    "source_text_confirmation",
    "intended_meaning",
    "reference_translation",
    "ambiguity_status",
    "reviewer_notes",
}

VALID_AMBIGUITY_STATUSES = {"none", "detected", "abstained"}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ImportIssue:
    row: int | None          # 1-based CSV data row; None = file-level
    field: str | None
    message: str
    example_id: str | None = None


@dataclass
class ImportResult:
    source_path: str
    reviewer_meta_path: str | None
    rows_examined: int = 0
    errors: list[ImportIssue] = field(default_factory=list)
    warnings: list[ImportIssue] = field(default_factory=list)
    merged_records: list[dict[str, Any]] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors

    @property
    def annotated_count(self) -> int:
        return len(self.merged_records)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _add(result: ImportResult, row: int | None, field_name: str | None,
         message: str, example_id: str | None = None, *, warning: bool = False) -> None:
    issue = ImportIssue(row=row, field=field_name, message=message, example_id=example_id)
    if warning:
        result.warnings.append(issue)
    else:
        result.errors.append(issue)


# ---------------------------------------------------------------------------
# Reviewer metadata validation
# ---------------------------------------------------------------------------

def _validate_reviewer_meta(meta: dict[str, str], result: ImportResult, *, row_number: int | None = None) -> bool:
    """Return True if reviewer metadata is structurally acceptable."""
    ok = True
    for key in sorted(REQUIRED_REVIEWER_FIELDS):
        if not _nonblank(meta.get(key)):
            _add(result, row_number, key,
                 f"reviewer metadata: '{key}' is required and must be non-blank")
            ok = False

    # Soft checks — warnings, not errors
    rid = meta.get("reviewer_id", "").strip()
    if rid.lower() in {"reviewer", "annotator", "unknown", "tbd", "test"}:
        _add(result, row_number, "reviewer_id",
             f"reviewer_id '{rid}' appears to be a placeholder; verify it is the actual reviewer's pseudonym",
             warning=True)

    saw = meta.get("saw_system_outputs", "").strip().lower()
    if saw not in {"no", "false", "0"}:
        _add(result, row_number, "saw_system_outputs",
             "reviewer metadata indicates the reviewer may have seen system outputs; "
             "reference translations prepared after seeing system outputs are not independent",
             warning=True)

    return ok


def _extract_reviewer_meta_from_rows(rows: list[dict[str, str]], result: ImportResult) -> dict[str, str]:
    """Collect reviewer metadata from CSV rows when no separate metadata file is supplied."""
    meta: dict[str, str] = {}
    for field in sorted(REQUIRED_REVIEWER_FIELDS):
        values = []
        for row in rows:
            if field in row and row.get(field) is not None:
                value = str(row.get(field, "")).strip()
                if value:
                    values.append(value)
        if not values:
            continue
        first_value = values[0]
        if any(value != first_value for value in values[1:]):
            _add(result, None, field,
                 "reviewer metadata fields disagree across CSV rows; a single reviewer submission must use a single reviewer identity and declarations",
                 example_id=None)
            continue
        meta[field] = first_value
    if meta:
        _validate_reviewer_meta(meta, result)
    return meta


def _validate_reviewer_metadata_columns(
    rows: list[dict[str, str]],
    fieldnames: list[str] | None,
    result: ImportResult,
    *,
    skip_if_external_meta: bool = False,
) -> None:
    """Reject missing or blank reviewer metadata regardless of where the metadata is stored."""
    if skip_if_external_meta:
        return
    available = set(fieldnames or [])
    for field in sorted(REQUIRED_REVIEWER_FIELDS):
        if field not in available:
            _add(result, None, field,
                 f"reviewer metadata: '{field}' is required and must be present in the CSV or reviewer metadata JSON")
            continue
        for row_number, row in enumerate(rows, start=2):
            value = str(row.get(field, "")).strip()
            if not value:
                _add(result, row_number, field,
                     f"reviewer metadata: '{field}' is required and must be non-blank")


# ---------------------------------------------------------------------------
# Per-row validation
# ---------------------------------------------------------------------------

def _validate_row(
    csv_row: dict[str, str],
    csv_row_number: int,
    pilot_records: dict[str, dict[str, Any]],
    seen_ids: set[str],
    result: ImportResult,
) -> dict[str, Any] | None:
    """Validate one CSV row against the original pilot record; return merged record or None."""
    example_id = csv_row.get("example_id", "").strip()

    # --- Required fields present ---
    for key in sorted(REQUIRED_PER_ROW_FIELDS):
        if key not in csv_row:
            _add(result, csv_row_number, key,
                 f"required column '{key}' missing from CSV row",
                 example_id=example_id or None)

    if not _nonblank(example_id):
        _add(result, csv_row_number, "example_id",
             "example_id is blank or missing; cannot match to pilot record")
        return None

    # --- Unknown ID ---
    if example_id not in pilot_records:
        _add(result, csv_row_number, "example_id",
             f"unknown example_id '{example_id}'; not present in source pilot dataset",
             example_id=example_id)
        return None

    # --- Duplicate ---
    if example_id in seen_ids:
        _add(result, csv_row_number, "example_id",
             f"duplicate example_id '{example_id}' in reviewer submission",
             example_id=example_id)
        return None
    seen_ids.add(example_id)

    original = pilot_records[example_id]

    # --- Source text must not change ---
    confirmed_text = csv_row.get("source_text_confirmation", "").strip()
    if confirmed_text != original["text"]:
        _add(result, csv_row_number, "source_text_confirmation",
             f"source text mismatch for '{example_id}': submission does not match original. "
             f"Original: {original['text']!r}. Submitted: {confirmed_text!r}",
             example_id=example_id)
        return None

    # --- Existing reviewed record must not be silently overwritten ---
    if original.get("annotation_status") == "reviewed":
        _add(result, csv_row_number, "example_id",
             f"record '{example_id}' is already reviewed; existing reviewed annotations "
             "must not be silently overwritten",
             example_id=example_id)
        return None

    # --- Reference translation required ---
    ref = csv_row.get("reference_translation", "").strip()
    if not ref:
        _add(result, csv_row_number, "reference_translation",
             f"reference_translation is empty for '{example_id}'; "
             "a non-empty English reference translation is required",
             example_id=example_id)

    # --- Intended meaning required ---
    meaning = csv_row.get("intended_meaning", "").strip()
    if not meaning:
        _add(result, csv_row_number, "intended_meaning",
             f"intended_meaning is empty for '{example_id}'; "
             "a non-empty intended-meaning statement is required",
             example_id=example_id)

    # --- Ambiguity status ---
    amb_status = csv_row.get("ambiguity_status", "").strip().lower()
    if amb_status not in VALID_AMBIGUITY_STATUSES:
        _add(result, csv_row_number, "ambiguity_status",
             f"ambiguity_status '{amb_status}' for '{example_id}' must be one of: "
             + ", ".join(sorted(VALID_AMBIGUITY_STATUSES)),
             example_id=example_id)

    # --- Exclusion flag ---
    exclude_flag = csv_row.get("exclude_recommendation", "").strip().lower()
    if exclude_flag in {"yes", "true", "1"}:
        _add(result, csv_row_number, "exclude_recommendation",
             f"record '{example_id}' is recommended for exclusion by the reviewer; "
             "it must be removed from the dataset before promotion",
             example_id=example_id, warning=True)

    # --- Label corrections (soft validation only — must be verified by validator) ---
    label_corrections = csv_row.get("label_corrections", "").strip()
    if label_corrections:
        _add(result, csv_row_number, "label_corrections",
             f"record '{example_id}' has label corrections recorded; "
             "tokens must be manually updated in the JSONL before promotion",
             example_id=example_id, warning=True)

    # --- Stop here if hard errors on this row ---
    if any(e.example_id == example_id and not isinstance(e, type(None))
           for e in result.errors
           if e.row == csv_row_number and e.field not in {"label_corrections"}):
        # Still allow partial build to accumulate all errors
        pass

    # --- Build merged record ---
    import copy
    merged = copy.deepcopy(original)

    # Preserve original draft annotations under a separate key
    merged["annotation_notes"] = (
        (merged.get("annotation_notes") or "")
        + "\n[Phase 29 import] Reviewer annotations recorded; "
          "status remains 'draft' until explicit promotion after review confirmation."
    ).strip()

    # Populate annotation_provenance.fields for reviewer-supplied fields
    provenance_fields = merged.setdefault("annotation_provenance", {}).setdefault("fields", {})

    if ref:
        merged["reference_translation"] = ref
        provenance_fields["reference_translation"] = {
            "origin": "human",
            "review_status": "not_reviewed",   # Status stays not_reviewed until explicit promotion
            "details": "Reviewer-supplied reference translation imported from reviewer CSV; "
                       "not yet independently verified for promotion.",
        }

    if meaning:
        merged["intended_meaning"] = meaning
        provenance_fields["intended_meaning"] = {
            "origin": "human",
            "review_status": "not_reviewed",
            "details": "Reviewer-supplied intended meaning imported from reviewer CSV; "
                       "not yet independently verified for promotion.",
        }

    # Ambiguity notes (recorded as annotation_notes; schema ambiguity field requires
    # full structured data that must be reviewed manually)
    alt_interpretations = csv_row.get("alternative_interpretations", "").strip()
    if alt_interpretations or amb_status in {"detected", "abstained"}:
        merged["annotation_notes"] = (
            merged.get("annotation_notes", "")
            + f"\n[Reviewer] Ambiguity status: {amb_status}."
            + (f" Alternatives: {alt_interpretations}" if alt_interpretations else "")
        ).strip()

    # Reviewer comments
    reviewer_notes = csv_row.get("reviewer_notes", "").strip()
    if reviewer_notes:
        merged["annotation_notes"] = (
            merged.get("annotation_notes", "")
            + f"\n[Reviewer notes] {reviewer_notes}"
        ).strip()

    # Protected entities
    protected = csv_row.get("protected_entities", "").strip()
    if protected:
        merged["annotation_notes"] = (
            merged.get("annotation_notes", "")
            + f"\n[Reviewer] Protected entities: {protected}"
        ).strip()

    # Label corrections note (corrections must be applied manually to tokens)
    if label_corrections:
        merged["annotation_notes"] = (
            merged.get("annotation_notes", "")
            + f"\n[Reviewer] Token label corrections required: {label_corrections}"
        ).strip()

    # review block: import stage keeps status 'not_reviewed'; reviewer must
    # explicitly change to 'reviewed' with their ID and date after verification.
    merged["review"] = {
        "status": "not_reviewed",
        "notes": (
            "Reviewer annotations imported from CSV. "
            "Reviewer must explicitly set status='reviewed', reviewer_id, and reviewed_at "
            "after verifying the merged content is correct. "
            "The importer cannot authenticate that a review occurred."
        ),
    }

    # annotation_status remains 'draft'; promotion is manual
    merged["annotation_status"] = "draft"

    return merged


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def import_reviewer_annotations(
    pilot_path: str | Path,
    csv_path: str | Path,
    reviewer_meta_path: str | Path | None = None,
) -> ImportResult:
    """
    Parse a completed reviewer CSV and merge annotations into pilot records.

    Parameters
    ----------
    pilot_path:
        Path to the original draft pilot JSONL.
    csv_path:
        Path to the completed reviewer annotation CSV.
    reviewer_meta_path:
        Optional path to a reviewer-metadata JSON file. When omitted, the CSV
        is expected to include the required reviewer metadata keys in each row.

    Returns
    -------
    ImportResult
        Contains validation errors/warnings and merged records.
        Merged records still carry annotation_status='draft'.
        No file is written; the caller decides where to persist results.
    """
    result = ImportResult(
        source_path=str(pilot_path),
        reviewer_meta_path=str(reviewer_meta_path) if reviewer_meta_path else None,
    )

    # --- Load original pilot records ---
    pilot_records: dict[str, dict[str, Any]] = {}
    try:
        for line in Path(pilot_path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if isinstance(record, dict) and isinstance(record.get("id"), str):
                pilot_records[record["id"]] = record
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _add(result, None, None, f"cannot read pilot dataset '{pilot_path}': {exc}")
        return result

    if not pilot_records:
        _add(result, None, None, f"pilot dataset '{pilot_path}' contains no records")
        return result

    # --- Parse CSV ---
    try:
        text = Path(csv_path).read_text(encoding="utf-8-sig")  # strip BOM if present
    except (OSError, UnicodeError) as exc:
        _add(result, None, None, f"cannot read reviewer CSV '{csv_path}': {exc}")
        return result

    try:
        reader = csv.DictReader(text.splitlines())
        rows = list(reader)
    except csv.Error as exc:
        _add(result, None, None, f"malformed CSV '{csv_path}': {exc}")
        return result

    if not rows:
        _add(result, None, None,
             f"reviewer CSV '{csv_path}' contains no data rows; "
             "has the reviewer completed and returned the file?")
        return result

    result.rows_examined = len(rows)

    # --- Load reviewer metadata (separate file or repeated CSV row values) ---
    reviewer_meta: dict[str, str] = {}
    if reviewer_meta_path:
        try:
            reviewer_meta = json.loads(
                Path(reviewer_meta_path).read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            _add(result, None, None,
                 f"cannot read reviewer metadata file '{reviewer_meta_path}': {exc}")
            return result
        if not isinstance(reviewer_meta, dict):
            _add(result, None, None,
                 "reviewer metadata file must be a JSON object")
            return result
        _validate_reviewer_meta(reviewer_meta, result)
        _validate_reviewer_metadata_columns(rows, list(reader.fieldnames or []), result, skip_if_external_meta=True)
    else:
        _validate_reviewer_metadata_columns(rows, list(reader.fieldnames or []), result)
        reviewer_meta = _extract_reviewer_meta_from_rows(rows, result)

    # --- Validate required reviewer metadata on each row, if present ---
    if reviewer_meta:
        for row_number, row in enumerate(rows, start=2):
            row_meta = {key: str(row.get(key, "")).strip() for key in REQUIRED_REVIEWER_FIELDS if key in row}
            if not row_meta:
                continue
            if any(not _nonblank(row_meta.get(key)) for key in REQUIRED_REVIEWER_FIELDS if key in row_meta):
                _validate_reviewer_meta(row_meta, result, row_number=row_number)

    # --- Validate and merge each row ---
    seen_ids: set[str] = set()
    for csv_row_number, csv_row in enumerate(rows, start=2):  # 2 = first data row after header
        merged = _validate_row(csv_row, csv_row_number, pilot_records, seen_ids, result)
        if merged is not None:
            result.merged_records.append(merged)

    return result


def write_reviewer_template(
    pilot_path: str | Path,
    output_path: str | Path | None = None,
) -> Path:
    """Create a blank reviewer CSV template populated with the original pilot IDs and source texts."""
    source = Path(pilot_path)
    try:
        rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read pilot dataset '{source}': {exc}") from exc

    fieldnames = [
        "example_id",
        "source_text_confirmation",
        "intended_meaning",
        "reference_translation",
        "ambiguity_status",
        "alternative_interpretations",
        "label_corrections",
        "reviewer_notes",
        "protected_entities",
        "normalization_judgment",
        "transliteration_judgment",
        "exclude_recommendation",
        "reviewer_id",
        "language_competency_declaration",
        "guideline_version",
        "saw_system_outputs",
        "independence_declaration",
    ]

    destination = Path(output_path) if output_path is not None else source.parent / "reviewer_annotation_template.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in rows:
            if not isinstance(record, dict) or not isinstance(record.get("id"), str):
                continue
            writer.writerow({
                "example_id": record.get("id", ""),
                "source_text_confirmation": record.get("text", ""),
                "intended_meaning": "",
                "reference_translation": "",
                "ambiguity_status": "",
                "alternative_interpretations": "",
                "label_corrections": "",
                "reviewer_notes": "",
                "protected_entities": "",
                "normalization_judgment": "",
                "transliteration_judgment": "",
                "exclude_recommendation": "",
                "reviewer_id": "",
                "language_competency_declaration": "",
                "guideline_version": "",
                "saw_system_outputs": "",
                "independence_declaration": "",
            })
    return destination


def write_merged_dataset(merged_records: list[dict[str, Any]], output: str | Path) -> Path:
    """
    Write merged draft annotations to a new JSONL file and validate structurally.

    The output file must not already exist (immutable-create convention).
    Annotation status remains 'draft' in the output.
    """
    output_path = Path(output)
    if output_path.exists():
        raise ValueError(f"output path already exists: {output_path}; choose a new path")
    if not output_path.parent.is_dir():
        raise ValueError(f"output directory does not exist: {output_path.parent}")
    if not merged_records:
        raise ValueError("no merged records to write")

    payload = "".join(
        json.dumps(record, ensure_ascii=False) + "\n"
        for record in merged_records
    ).encode("utf-8")
    output_path.write_bytes(payload)

    # Structural validation — merged output must still be structurally valid
    report = validate_dataset(output_path)
    if not report.valid:
        output_path.unlink(missing_ok=True)
        raise ValueError(
            "merged dataset failed structural validation after import; "
            "file not written. Errors: "
            + "; ".join(issue.message for issue in report.errors)
        )
    return output_path
