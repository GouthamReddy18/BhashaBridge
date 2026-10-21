"""Read-only validation for BhashaBridge annotation JSONL datasets."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from app.services.preprocessing import normalize_whitespace
from app.services.tokenization import tokenize

VERSION = "1.0"
LABELS = {"TELUGU_ROMANIZED", "TELUGU_SCRIPT", "ENGLISH", "PUNCTUATION", "NUMBER", "OTHER", "UNKNOWN"}
RECORD_FIELDS = {"annotation_version", "id", "text", "normalized_text", "source_type", "annotation_status", "annotation_provenance", "tokens", "romanized_interpretation", "telugu_script_equivalent", "ambiguity", "reference_translation", "intended_meaning", "split", "split_group", "annotation_notes", "review"}
LINGUISTIC_FIELDS = {"romanized_interpretation", "telugu_script_equivalent", "ambiguity", "reference_translation", "intended_meaning"}
SPLITS = {"train", "validation", "test"}
ORIGINS = {"human", "machine", "human_and_machine"}

@dataclass(frozen=True)
class ValidationIssue:
    line: int
    message: str
    record_id: str | None = None

@dataclass
class ValidationReport:
    path: str
    records_examined: int = 0
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    @property
    def valid(self) -> bool:
        return not self.errors

def _add(report, line, message, record_id=None, *, warning=False):
    issue = ValidationIssue(line, message, record_id)
    (report.warnings if warning else report.errors).append(issue)

def _nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())

def _canonical_iso_date(value: Any) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False

class DuplicateJSONKeyError(ValueError):
    """A JSON object repeats a member name."""

def _unique_object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJSONKeyError(f"duplicate JSON object key {key!r}")
        result[key] = value
    return result

def _check_properties(value, allowed, required, report, line, rid, prefix):
    for key in sorted(value.keys() - allowed):
        _add(report, line, f"{prefix} has unsupported property: {key}", rid)
    for key in sorted(required - value.keys()):
        _add(report, line, f"{prefix} missing required field: {key}", rid)

def _validate_ambiguity(value, report, line, rid):
    if value is None:
        return
    if not isinstance(value, dict):
        _add(report, line, "ambiguity must be an object or null", rid); return
    allowed = {"status", "candidates", "selected_candidate", "evidence", "rule_id"}
    _check_properties(value, allowed, allowed, report, line, rid, "ambiguity")
    candidates = value.get("candidates")
    if not isinstance(candidates, list):
        _add(report, line, "ambiguity.candidates must be an array", rid); candidates = []
    ids = set()
    for i, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            _add(report, line, f"ambiguity.candidates[{i}] must be an object", rid); continue
        required_candidate = {"candidate_id", "meaning", "source"}
        _check_properties(candidate, required_candidate, required_candidate, report, line, rid, f"ambiguity.candidates[{i}]")
        cid = candidate.get("candidate_id")
        if not _nonblank(cid):
            _add(report, line, f"ambiguity.candidates[{i}].candidate_id must be nonblank", rid)
        elif cid in ids:
            _add(report, line, f"duplicate ambiguity candidate_id: {cid}", rid)
        else:
            ids.add(cid)
        for key in ("meaning", "source"):
            if not _nonblank(candidate.get(key)):
                _add(report, line, f"ambiguity.candidates[{i}].{key} must be nonblank", rid)
    if len(ids) < 2:
        _add(report, line, "ambiguity requires at least two distinct candidate IDs", rid)
    status, selected = value.get("status"), value.get("selected_candidate")
    if not isinstance(status, str) or status not in {"detected", "resolved", "abstained"}:
        _add(report, line, "ambiguity.status must be detected, resolved, or abstained", rid)
    elif status == "resolved":
        if not isinstance(selected, str) or selected not in ids:
            _add(report, line, "resolved ambiguity must select a listed candidate_id", rid)
    elif selected is not None:
        _add(report, line, f"{status} ambiguity must have selected_candidate null", rid)
    for key in ("evidence", "rule_id"):
        if not _nonblank(value.get(key)):
            _add(report, line, f"ambiguity.{key} must be nonblank", rid)

def _validate_review(record_status, review, report, line, rid):
    if review is None:
        if record_status == "reviewed": _add(report, line, "reviewed annotation_status requires review metadata", rid)
        return None
    if not isinstance(review, dict):
        _add(report, line, "review must be an object or null", rid); return None
    allowed = {"status", "reviewer_id", "reviewed_at", "notes"}
    _check_properties(review, allowed, {"status"}, report, line, rid, "review")
    state = review.get("status")
    if not isinstance(state, str) or state not in {"not_reviewed", "reviewed", "disputed"}:
        _add(report, line, "review.status must be not_reviewed, reviewed, or disputed", rid); return None
    reviewer, reviewed_at = review.get("reviewer_id"), review.get("reviewed_at")
    if reviewer is not None and not _nonblank(reviewer): _add(report, line, "review.reviewer_id must be nonblank when supplied", rid)
    if reviewed_at is not None and not _canonical_iso_date(reviewed_at): _add(report, line, "review.reviewed_at must be a valid YYYY-MM-DD calendar date", rid)
    if review.get("notes") is not None and not isinstance(review.get("notes"), str): _add(report, line, "review.notes must be a string when supplied", rid)
    if state == "reviewed":
        if record_status != "reviewed": _add(report, line, "review.status reviewed requires annotation_status reviewed", rid)
        if not _nonblank(reviewer): _add(report, line, "reviewed records require a supplied reviewer_id", rid)
        if not _canonical_iso_date(reviewed_at): _add(report, line, "reviewed records require reviewed_at as YYYY-MM-DD", rid)
    elif state == "disputed":
        if record_status != "draft": _add(report, line, "disputed review must remain annotation_status draft", rid)
        if not _nonblank(reviewer) or not _canonical_iso_date(reviewed_at): _add(report, line, "disputed review requires reviewer_id and reviewed_at", rid)
    else:
        if record_status != "draft": _add(report, line, "not_reviewed state requires annotation_status draft", rid)
        if reviewer is not None or reviewed_at is not None: _add(report, line, "not_reviewed state cannot contain reviewer_id or reviewed_at", rid)
    return state

def _validate_field_provenance(record, provenance, record_status, review_status, report, line, rid):
    if not isinstance(provenance, dict): return
    fields = provenance.get("fields", {})
    if not isinstance(fields, dict):
        _add(report, line, "annotation_provenance.fields must be an object", rid); return
    for name in sorted(fields.keys() - LINGUISTIC_FIELDS): _add(report, line, f"annotation_provenance.fields has unsupported field: {name}", rid)
    for name in sorted(LINGUISTIC_FIELDS):
        annotated = record.get(name) is not None
        info = fields.get(name)
        if annotated and info is None:
            _add(report, line, f"{name} requires matching annotation_provenance.fields metadata", rid); continue
        if not annotated and name in fields:
            _add(report, line, f"annotation_provenance.fields.{name} exists without an annotation", rid); continue
        if not annotated: continue
        if not isinstance(info, dict):
            _add(report, line, f"annotation_provenance.fields.{name} must be an object", rid); continue
        allowed = {"origin", "review_status", "details", "source_reference"}
        required = {"origin", "review_status", "details"}
        _check_properties(info, allowed, required, report, line, rid, f"annotation_provenance.fields.{name}")
        origin, state = info.get("origin"), info.get("review_status")
        if not isinstance(origin, str) or origin not in ORIGINS: _add(report, line, f"{name} origin must be human, machine, or human_and_machine", rid)
        if not isinstance(state, str) or state not in {"not_reviewed", "reviewed"}: _add(report, line, f"{name} review_status must be not_reviewed or reviewed", rid)
        if not _nonblank(info.get("details")): _add(report, line, f"{name} provenance details must be nonblank", rid)
        if info.get("source_reference") is not None and not _nonblank(info.get("source_reference")): _add(report, line, f"{name} source_reference must be nonblank when supplied", rid)
        if state == "reviewed" and (record_status != "reviewed" or review_status != "reviewed"): _add(report, line, f"{name} cannot be marked reviewed without reviewed record metadata", rid)
        if record_status == "reviewed" and state != "reviewed": _add(report, line, f"reviewed record requires {name} provenance review_status reviewed", rid)
        if name == "reference_translation":
            if origin not in {"human", "human_and_machine"}: _add(report, line, "reference_translation cannot be machine-only", rid)
            if state != "reviewed" or record_status != "reviewed" or review_status != "reviewed": _add(report, line, "reference_translation requires a reviewed record and reviewed field provenance", rid)
            if not _nonblank(info.get("source_reference")): _add(report, line, "reference_translation requires source_reference provenance", rid)
        if name == "intended_meaning":
            if origin not in {"human", "human_and_machine"}: _add(report, line, "intended_meaning cannot be machine-only", rid)
            if state != "reviewed" or record_status != "reviewed" or review_status != "reviewed": _add(report, line, "intended_meaning requires a reviewed record and reviewed field provenance", rid)
            if not _nonblank(info.get("source_reference")): _add(report, line, "intended_meaning requires source_reference provenance", rid)

def _validate_record(obj: Any, line: int, report: ValidationReport, seen: set[str]) -> None:
    if not isinstance(obj, dict): _add(report, line, "record must be a JSON object"); return
    rid = obj.get("id") if isinstance(obj.get("id"), str) else None
    required = {"annotation_version", "id", "text", "normalized_text", "source_type", "annotation_status", "annotation_provenance", "tokens"}
    _check_properties(obj, RECORD_FIELDS, required, report, line, rid, "record")
    for key in ("id", "text", "normalized_text", "source_type"):
        if not _nonblank(obj.get(key)): _add(report, line, f"{key} must be a nonblank string", rid)
    if _nonblank(rid):
        if rid in seen: _add(report, line, f"duplicate record id: {rid}", rid)
        else: seen.add(rid)
    text, normalized = obj.get("text"), obj.get("normalized_text")
    if isinstance(text, str) and isinstance(normalized, str) and normalize_whitespace(text) != normalized:
        _add(report, line, "normalized_text does not match project whitespace normalization", rid)
    status = obj.get("annotation_status")
    if not isinstance(status, str) or status not in {"draft", "reviewed"}: _add(report, line, "annotation_status must be draft or reviewed", rid)
    if obj.get("annotation_version") != VERSION: _add(report, line, f"unsupported annotation_version; expected {VERSION}", rid)
    review_status = _validate_review(status, obj.get("review"), report, line, rid)
    provenance = obj.get("annotation_provenance")
    if not isinstance(provenance, dict):
        _add(report, line, "annotation_provenance must be an object", rid)
    else:
        _check_properties(provenance, {"method", "details", "origin", "fields"}, {"method", "details", "origin"}, report, line, rid, "annotation_provenance")
        for key in ("method", "details"):
            if not _nonblank(provenance.get(key)): _add(report, line, f"annotation_provenance.{key} must be nonblank", rid)
        origin = provenance.get("origin")
        if not isinstance(origin, str) or origin not in ORIGINS: _add(report, line, "annotation_provenance.origin must be human, machine, or human_and_machine", rid)
    tokens = obj.get("tokens")
    if not isinstance(tokens, list): _add(report, line, "tokens must be an array", rid)
    elif isinstance(normalized, str):
        expected = tokenize(normalized)
        if len(tokens) != len(expected): _add(report, line, f"token count does not match project tokenizer ({len(expected)} expected)", rid)
        previous_end = 0
        for index, token in enumerate(tokens):
            if not isinstance(token, dict): _add(report, line, f"tokens[{index}] must be an object", rid); continue
            token_fields = {"index", "surface", "start", "end", "language_label"}
            _check_properties(token, token_fields, token_fields, report, line, rid, f"tokens[{index}]")
            if isinstance(token.get("index"), bool) or token.get("index") != index: _add(report, line, f"tokens[{index}].index must equal {index}", rid)
            label = token.get("language_label")
            if not isinstance(label, str) or label not in LABELS: _add(report, line, f"tokens[{index}] has unsupported language_label", rid)
            start, end = token.get("start"), token.get("end")
            if any(isinstance(v, bool) or not isinstance(v, int) for v in (start, end)):
                _add(report, line, f"tokens[{index}] start/end must be integers", rid); continue
            if start < 0 or end <= start or end > len(normalized): _add(report, line, f"tokens[{index}] has invalid span [{start}, {end})", rid); continue
            if start < previous_end: _add(report, line, f"tokens[{index}] overlaps or is out of order", rid)
            previous_end = end
            surface = token.get("surface")
            if not _nonblank(surface) or normalized[start:end] != surface: _add(report, line, f"tokens[{index}].surface does not match normalized-text slice", rid)
            if index < len(expected) and (start, end, surface) != (expected[index].start, expected[index].end, expected[index].text): _add(report, line, f"tokens[{index}] does not match project tokenizer boundaries", rid)
    for name in ("romanized_interpretation", "telugu_script_equivalent", "reference_translation", "intended_meaning"):
        if name in obj and obj[name] is not None and not _nonblank(obj[name]): _add(report, line, f"{name} must be a nonblank string or null", rid)
    if "split" in obj and (not isinstance(obj["split"], str) or obj["split"] not in SPLITS): _add(report, line, "split must be train, validation, or test", rid)
    if "split_group" in obj and not _nonblank(obj["split_group"]): _add(report, line, "split_group must be a nonblank string when supplied", rid)
    if "annotation_notes" in obj and not _nonblank(obj["annotation_notes"]): _add(report, line, "annotation_notes must be a nonblank string when supplied", rid)
    _validate_ambiguity(obj.get("ambiguity"), report, line, rid)
    _validate_field_provenance(obj, provenance, status, review_status, report, line, rid)
    if status == "draft": _add(report, line, "draft is unreviewed; do not treat as ground truth", rid, warning=True)

def validate_dataset(path: str | Path) -> ValidationReport:
    """Validate UTF-8 JSONL read-only, continuing after invalid lines."""
    source = Path(path); report = ValidationReport(str(source)); seen: set[str] = set()
    try:
        with source.open(encoding="utf-8") as stream:
            for line, raw in enumerate(stream, start=1):
                if not raw.strip(): continue
                report.records_examined += 1
                try: record = json.loads(raw, object_pairs_hook=_unique_object_pairs)
                except DuplicateJSONKeyError as exc: _add(report, line, str(exc)); continue
                except json.JSONDecodeError as exc: _add(report, line, f"malformed JSON: {exc.msg} (column {exc.colno})"); continue
                _validate_record(record, line, report, seen)
    except (OSError, UnicodeError) as exc: _add(report, 0, f"cannot read dataset: {exc}")
    return report
