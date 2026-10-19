"""Read-only validation for BhashaBridge annotation JSONL datasets."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any
from app.services.preprocessing import normalize_whitespace
from app.services.tokenization import tokenize

VERSION = "1.0"
LABELS = {"TELUGU_ROMANIZED", "TELUGU_SCRIPT", "ENGLISH", "PUNCTUATION", "NUMBER", "OTHER", "UNKNOWN"}

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

def _add(report, line, message, record_id=None, warning=False):
    issue = ValidationIssue(line, message, record_id)
    (report.warnings if warning else report.errors).append(issue)

def _text(value):
    return isinstance(value, str) and bool(value.strip())

def _iso_date(value):
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False

def _validate_ambiguity(value, report, line, rid):
    if value is None:
        return
    if not isinstance(value, dict):
        _add(report, line, "ambiguity must be an object or null", rid); return
    candidates = value.get("candidates")
    if not isinstance(candidates, list):
        _add(report, line, "ambiguity.candidates must be an array", rid); candidates = []
    ids = set()
    for i, candidate in enumerate(candidates):
        if not isinstance(candidate, dict) or not _text(candidate.get("candidate_id")):
            _add(report, line, f"ambiguity.candidates[{i}] needs candidate_id", rid); continue
        cid = candidate["candidate_id"]
        if cid in ids: _add(report, line, f"duplicate ambiguity candidate_id: {cid}", rid)
        ids.add(cid)
        if not _text(candidate.get("meaning")) or not _text(candidate.get("source")):
            _add(report, line, f"ambiguity.candidates[{i}] needs meaning and source", rid)
    status, selected = value.get("status"), value.get("selected_candidate")
    if not isinstance(status, str) or status not in {"detected", "resolved", "abstained"}:
        _add(report, line, "ambiguity.status must be detected, resolved, or abstained", rid)
    elif status == "resolved" and (not isinstance(selected, str) or selected not in ids):
        _add(report, line, "resolved ambiguity must select a listed candidate_id", rid)
    elif status in {"detected", "abstained"} and selected is not None:
        _add(report, line, f"{status} ambiguity must not select a candidate", rid)
    if len(ids) < 2: _add(report, line, "ambiguity requires at least two distinct candidates", rid)
    for key in ("evidence", "rule_id"):
        if not _text(value.get(key)): _add(report, line, f"ambiguity.{key} must be a non-empty string", rid)

def _validate_record(obj: Any, line: int, report: ValidationReport, seen: set[str]) -> None:
    if not isinstance(obj, dict): _add(report, line, "record must be a JSON object"); return
    rid = obj.get("id") if isinstance(obj.get("id"), str) else None
    allowed = {"annotation_version", "id", "text", "normalized_text", "source_type", "annotation_status", "annotation_provenance", "tokens", "romanized_interpretation", "telugu_script_equivalent", "ambiguity", "reference_translation", "annotation_notes", "review"}
    for key in sorted(obj.keys() - allowed): _add(report, line, f"unsupported record field: {key}", obj.get("id") if isinstance(obj.get("id"), str) else None)
    required = {"annotation_version", "id", "text", "normalized_text", "source_type", "annotation_status", "annotation_provenance", "tokens"}
    for key in sorted(required - obj.keys()): _add(report, line, f"missing required field: {key}", rid)
    if not _text(obj.get("id")): _add(report, line, "id must be a non-empty string", rid)
    elif rid in seen: _add(report, line, f"duplicate record id: {rid}", rid)
    else: seen.add(rid)
    text, normalized = obj.get("text"), obj.get("normalized_text")
    if not _text(text): _add(report, line, "text must be a non-empty string", rid)
    if not _text(normalized): _add(report, line, "normalized_text must be a non-empty string", rid)
    elif isinstance(text, str) and normalize_whitespace(text) != normalized:
        _add(report, line, "normalized_text does not match project whitespace normalization", rid)
    if not _text(obj.get("source_type")): _add(report, line, "source_type must be a non-empty string", rid)
    status = obj.get("annotation_status")
    if not isinstance(status, str) or status not in {"draft", "reviewed"}: _add(report, line, "annotation_status must be draft or reviewed", rid)
    if obj.get("annotation_version") != VERSION: _add(report, line, f"unsupported annotation_version; expected {VERSION}", rid)
    provenance = obj.get("annotation_provenance")
    if not isinstance(provenance, dict): _add(report, line, "annotation_provenance must be an object", rid)
    else:
        for key in ("method", "details"):
            if not _text(provenance.get(key)): _add(report, line, f"annotation_provenance.{key} must be a non-empty string", rid)
    tokens = obj.get("tokens")
    if not isinstance(tokens, list): _add(report, line, "tokens must be an array", rid)
    elif isinstance(normalized, str):
        expected = tokenize(normalized)
        if len(tokens) != len(expected): _add(report, line, f"token count does not match project tokenizer ({len(expected)} expected)", rid)
        previous_end = 0
        for i, token in enumerate(tokens):
            if not isinstance(token, dict): _add(report, line, f"tokens[{i}] must be an object", rid); continue
            for key in ("index", "surface", "start", "end", "language_label"):
                if key not in token: _add(report, line, f"tokens[{i}] missing {key}", rid)
            if isinstance(token.get("index"), bool) or token.get("index") != i: _add(report, line, f"tokens[{i}].index must equal {i}", rid)
            if not isinstance(token.get("language_label"), str) or token.get("language_label") not in LABELS: _add(report, line, f"tokens[{i}] has unsupported language_label", rid)
            start, end = token.get("start"), token.get("end")
            if any(isinstance(x, bool) or not isinstance(x, int) for x in (start, end)):
                _add(report, line, f"tokens[{i}] start/end must be integers", rid); continue
            if start < 0 or end <= start or end > len(normalized): _add(report, line, f"tokens[{i}] has invalid span [{start}, {end})", rid); continue
            if start < previous_end: _add(report, line, f"tokens[{i}] overlaps or is out of order", rid)
            previous_end = end
            surface = token.get("surface")
            if not isinstance(surface, str) or normalized[start:end] != surface: _add(report, line, f"tokens[{i}].surface does not match normalized-text slice", rid)
            if i < len(expected) and (start, end, surface) != (expected[i].start, expected[i].end, expected[i].text):
                _add(report, line, f"tokens[{i}] does not match project tokenizer boundaries", rid)
    for key in ("romanized_interpretation", "telugu_script_equivalent", "reference_translation"):
        if obj.get(key) is not None and not isinstance(obj[key], str): _add(report, line, f"{key} must be a string or null", rid)
    _validate_ambiguity(obj.get("ambiguity"), report, line, rid)
    review = obj.get("review")
    if review is not None:
        if not isinstance(review, dict): _add(report, line, "review must be an object or null", rid)
        else:
            rstatus = review.get("status")
            if not isinstance(rstatus, str) or rstatus not in {"not_reviewed", "reviewed", "disputed"}: _add(report, line, "review.status is invalid", rid)
            reviewer, reviewed_at = review.get("reviewer_id"), review.get("reviewed_at")
            if rstatus == "reviewed":
                if not _text(reviewer): _add(report, line, "reviewed records require supplied reviewer_id", rid)
                if not _iso_date(reviewed_at): _add(report, line, "reviewed records require ISO reviewed_at", rid)
                if status != "reviewed": _add(report, line, "review.status conflicts with annotation_status", rid)
            elif status == "reviewed": _add(report, line, "reviewed annotation_status requires review.status reviewed", rid)
            if reviewer is not None and not _text(reviewer): _add(report, line, "reviewer_id must be non-empty when supplied", rid)
            if reviewed_at is not None and not _iso_date(reviewed_at): _add(report, line, "reviewed_at must be ISO date when supplied", rid)
            if review.get("notes") is not None and not isinstance(review["notes"], str): _add(report, line, "review.notes must be a string", rid)
    elif status == "reviewed": _add(report, line, "reviewed annotation_status requires review metadata", rid)
    if status == "draft": _add(report, line, "draft is unreviewed; do not treat as ground truth", rid, warning=True)

def validate_dataset(path: str | Path) -> ValidationReport:
    """Validate UTF-8 JSONL read-only, returning line-specific errors/warnings."""
    source = Path(path); report = ValidationReport(str(source)); seen: set[str] = set()
    try:
        with source.open(encoding="utf-8") as stream:
            for line, raw in enumerate(stream, 1):
                if not raw.strip(): continue
                report.records_examined += 1
                try: obj = json.loads(raw)
                except json.JSONDecodeError as exc:
                    _add(report, line, f"malformed JSON: {exc.msg} (column {exc.colno})"); continue
                _validate_record(obj, line, report, seen)
    except (OSError, UnicodeError) as exc: _add(report, 0, f"cannot read dataset: {exc}")
    return report
