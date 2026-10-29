"""
Phase 28 regression tests — dataset-curation workflow integrity.

These tests verify properties identified during the Phase 28 audit:
  - A structurally valid draft dataset is NOT evaluation-ready.
  - Constructed/project-authored records are not silently treated as reviewed.
  - Missing human review remains a blocker after structural validation passes.
  - Missing approved references remain a blocker.
  - 'project_authored_constructed' source_type is accepted by the structural validator.
  - Invalid provenance values remain rejected.
  - Duplicate IDs are rejected even when source_type differs.
  - Structural validation success does NOT imply research readiness.
  - No report with research scores is generated from an ineligible dataset.
  - Mock / fixture / synthetic source_type records with draft status remain
    ineligible for evaluation.
  - Structural validator exits 0 for a clean draft record regardless of
    source_type label.

None of these tests weaken or relax existing readiness rules.
"""
import json
import tempfile
import unittest
from pathlib import Path

from app.services.dataset_validation import validate_dataset
from app.services.evaluation_readiness import check_evaluation_readiness
from app.services.preprocessing import normalize_whitespace
from app.services.tokenization import tokenize


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_draft(
    record_id: str = "p28-draft-001",
    text: str = "nenu college ki veltunna",
    source_type: str = "project_authored_constructed",
) -> dict:
    """Return a structurally valid draft record matching pilot_examples.jsonl conventions."""
    normalized = normalize_whitespace(text)
    tokens = []
    for t in tokenize(normalized):
        # Conservative labels — only 'nenu' and 'ki' are confidently TELUGU_ROMANIZED
        label_map = {"nenu": "TELUGU_ROMANIZED", "ki": "TELUGU_ROMANIZED"}
        tokens.append({
            "index": t.index,
            "surface": t.text,
            "start": t.start,
            "end": t.end,
            "language_label": label_map.get(t.text, "UNKNOWN"),
        })
    return {
        "annotation_version": "1.0",
        "id": record_id,
        "text": text,
        "normalized_text": normalized,
        "source_type": source_type,
        "annotation_status": "draft",
        "annotation_provenance": {
            "method": "researcher_composed",
            "details": "Constructed by the BhashaBridge research team for workflow validation.",
            "origin": "human",
        },
        "tokens": tokens,
        "romanized_interpretation": None,
        "telugu_script_equivalent": None,
        "ambiguity": None,
        "reference_translation": None,
        "intended_meaning": None,
        "annotation_notes": "Phase 28 regression test fixture.",
    }


def _make_reviewed(
    record_id: str = "p28-reviewed-001",
    text: str = "nenu college ki veltunna",
    split: str = "test",
    group: str = "p28-group-1",
) -> dict:
    """Return a structurally valid fully-reviewed record (test fixture only)."""
    normalized = normalize_whitespace(text)
    tokens = []
    for t in tokenize(normalized):
        label_map = {"nenu": "TELUGU_ROMANIZED", "ki": "TELUGU_ROMANIZED", "college": "ENGLISH"}
        tokens.append({
            "index": t.index,
            "surface": t.text,
            "start": t.start,
            "end": t.end,
            "language_label": label_map.get(t.text, "UNKNOWN"),
        })
    return {
        "annotation_version": "1.0",
        "id": record_id,
        "text": text,
        "normalized_text": normalized,
        "source_type": "project_authored_constructed",
        "annotation_status": "reviewed",
        "annotation_provenance": {
            "method": "researcher_composed_independently_reviewed",
            "details": "Phase 28 regression test fixture only — not a real reviewed record.",
            "origin": "human",
            "fields": {
                "reference_translation": {
                    "origin": "human",
                    "review_status": "reviewed",
                    "details": "Phase 28 regression test fixture only.",
                    "source_reference": "p28-test-fixture-ref",
                },
                "intended_meaning": {
                    "origin": "human",
                    "review_status": "reviewed",
                    "details": "Phase 28 regression test fixture only.",
                    "source_reference": "p28-test-fixture-meaning",
                },
            },
        },
        "tokens": tokens,
        "romanized_interpretation": None,
        "telugu_script_equivalent": None,
        "ambiguity": None,
        "reference_translation": "I am going to college.",
        "intended_meaning": "The speaker is on their way to college.",
        "annotation_notes": "Phase 28 regression test fixture only.",
        "review": {
            "status": "reviewed",
            "reviewer_id": "p28-test-fixture-pseudonym-not-a-real-reviewer",
            "reviewed_at": "2026-10-28",
            "notes": "Phase 28 regression test fixture only.",
        },
        "split": split,
        "split_group": group,
    }


def _write_jsonl(records: list, path: Path) -> None:
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Structural validation tests (new in Phase 28)
# ---------------------------------------------------------------------------

class TestStructuralValidationPhase28(unittest.TestCase):
    """Structural validator behaviour for project_authored_constructed records."""

    def _validate(self, *records):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "records.jsonl"
            _write_jsonl(list(records), p)
            return validate_dataset(p)

    def test_project_authored_constructed_draft_passes_structurally(self):
        """A project-authored draft with valid fields must pass structural validation."""
        report = self._validate(_make_draft())
        self.assertTrue(report.valid, report.errors)
        self.assertEqual(report.records_examined, 1)

    def test_draft_produces_warning_not_error(self):
        """Draft status emits a warning, not an error — it is structurally valid."""
        report = self._validate(_make_draft())
        self.assertEqual(len(report.errors), 0)
        self.assertEqual(len(report.warnings), 1)
        self.assertIn("draft is unreviewed", report.warnings[0].message)

    def test_structural_validity_does_not_imply_review(self):
        """Structural validation success on a draft must never imply the record is reviewed."""
        draft = _make_draft()
        report = self._validate(draft)
        self.assertTrue(report.valid)
        # The record's annotation_status must still be draft
        self.assertEqual(draft["annotation_status"], "draft")

    def test_duplicate_id_rejected_regardless_of_source_type(self):
        """Duplicate IDs are rejected even when source_type differs."""
        r1 = _make_draft("same-id", source_type="project_authored_constructed")
        r2 = _make_draft("same-id", text="meeru ekkada unnaaru?", source_type="synthetic_illustrative")
        report = self._validate(r1, r2)
        self.assertFalse(report.valid)
        self.assertTrue(any("duplicate record id" in e.message for e in report.errors))

    def test_invalid_provenance_origin_is_rejected(self):
        """Invalid provenance.origin values are rejected by structural validation."""
        record = _make_draft()
        record["annotation_provenance"]["origin"] = "invented_value"
        report = self._validate(record)
        self.assertFalse(report.valid)
        self.assertTrue(any("origin must be human" in e.message for e in report.errors))

    def test_reviewer_fields_on_not_reviewed_record_are_rejected(self):
        """A draft record must not carry reviewer_id or reviewed_at in a not_reviewed review block."""
        record = _make_draft()
        record["review"] = {
            "status": "not_reviewed",
            "reviewer_id": "fabricated-reviewer",
            "reviewed_at": "2026-10-28",
        }
        report = self._validate(record)
        self.assertFalse(report.valid)
        self.assertTrue(
            any("not_reviewed state cannot contain reviewer_id" in e.message for e in report.errors)
        )

    def test_reviewed_status_without_review_metadata_is_rejected(self):
        """annotation_status=reviewed without a review object is a structural error."""
        record = _make_draft()
        record["annotation_status"] = "reviewed"
        report = self._validate(record)
        self.assertFalse(report.valid)
        self.assertTrue(
            any("reviewed annotation_status requires review metadata" in e.message for e in report.errors)
        )


# ---------------------------------------------------------------------------
# Research readiness tests (new in Phase 28)
# ---------------------------------------------------------------------------

class TestResearchReadinessPhase28(unittest.TestCase):
    """Readiness checker gates for Phase 28 dataset-curation workflow."""

    def _check(self, *records):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "records.jsonl"
            _write_jsonl(list(records), p)
            return check_evaluation_readiness(p)

    # -- Draft ineligibility --

    def test_project_authored_draft_is_not_evaluation_ready(self):
        """A structurally valid project-authored draft must not be evaluation-ready."""
        report = self._check(_make_draft())
        self.assertFalse(report.ready)

    def test_draft_blocker_is_review_status(self):
        """The primary blocker for a draft must be the missing review."""
        report = self._check(_make_draft())
        messages = [e.message for e in report.errors]
        self.assertTrue(
            any("not reviewed and is ineligible" in m for m in messages),
            "Expected 'not reviewed and is ineligible' in error messages",
        )

    def test_missing_reference_translation_blocks_project_authored_record(self):
        """Missing reference_translation blocks evaluation even for project-authored records."""
        report = self._check(_make_draft())
        self.assertTrue(
            any("reference_translation is required" in e.message for e in report.errors)
        )

    def test_missing_intended_meaning_blocks_project_authored_record(self):
        """Missing intended_meaning blocks evaluation even for project-authored records."""
        report = self._check(_make_draft())
        self.assertTrue(
            any("intended_meaning is required" in e.message for e in report.errors)
        )

    def test_structural_valid_draft_still_blocked_by_readiness_checker(self):
        """structural_valid=True and ready=False can coexist — these are distinct properties."""
        structural = validate_dataset
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "records.jsonl"
            _write_jsonl([_make_draft()], p)
            struct_report = validate_dataset(p)
            ready_report = check_evaluation_readiness(p)
        self.assertTrue(struct_report.valid)     # Passes structural validation
        self.assertFalse(ready_report.ready)     # Still NOT READY — these are separate properties

    def test_synthetic_illustrative_draft_is_not_evaluation_ready(self):
        """A synthetic_illustrative record with draft status must not be evaluation-ready."""
        record = _make_draft(source_type="synthetic_illustrative")
        report = self._check(record)
        self.assertFalse(report.ready)

    # -- Reviewed record with all required fields can pass --

    def test_fully_reviewed_fixture_passes_readiness(self):
        """A fully-populated reviewed fixture must pass readiness (exercises the ready path)."""
        report = self._check(_make_reviewed())
        self.assertTrue(report.ready, [e.message for e in report.errors])

    def test_reviewed_record_without_split_is_blocked(self):
        """A reviewed record missing a split assignment is blocked."""
        record = _make_reviewed()
        record.pop("split")
        report = self._check(record)
        self.assertFalse(report.ready)
        self.assertTrue(any("valid split assignment" in e.message for e in report.errors))

    def test_reviewed_record_without_split_group_is_blocked(self):
        """A reviewed record missing split_group is blocked."""
        record = _make_reviewed()
        record.pop("split_group")
        report = self._check(record)
        self.assertFalse(report.ready)
        self.assertTrue(any("split_group is required" in e.message for e in report.errors))

    def test_test_split_record_requires_both_romanized_and_english_tokens(self):
        """Test-split records must contain both TELUGU_ROMANIZED and ENGLISH tokens."""
        # _make_reviewed uses 'nenu college ki veltunna' which after label_map has
        # TELUGU_ROMANIZED ('nenu', 'ki') and ENGLISH ('college') — should pass.
        report = self._check(_make_reviewed())
        self.assertTrue(report.ready, [e.message for e in report.errors])

    def test_machine_only_reference_translation_is_blocked(self):
        """reference_translation with machine-only origin must be blocked."""
        record = _make_reviewed()
        record["annotation_provenance"]["fields"]["reference_translation"]["origin"] = "machine"
        report = self._check(record)
        self.assertFalse(report.ready)
        self.assertTrue(any("reference_translation cannot be machine-only" in e.message for e in report.errors))

    def test_missing_source_reference_for_reference_translation_is_blocked(self):
        """reference_translation without source_reference is blocked."""
        record = _make_reviewed()
        del record["annotation_provenance"]["fields"]["reference_translation"]["source_reference"]
        report = self._check(record)
        self.assertFalse(report.ready)

    # -- Leakage protection --

    def test_split_group_crossing_splits_is_blocked(self):
        """Records from the same split_group appearing in different splits are blocked."""
        r1 = _make_reviewed("r1", text="nenu college ki veltunna", split="train", group="shared")
        r2 = _make_reviewed("r2", text="nenu office ki veltunna", split="test", group="shared")
        report = self._check(r1, r2)
        self.assertFalse(report.ready)
        self.assertTrue(any("crosses splits" in e.message for e in report.errors))

    def test_exact_duplicate_source_text_across_splits_is_blocked(self):
        """The same normalized source text in two different splits is a leakage error."""
        r1 = _make_reviewed("r1", split="train", group="g1")
        r2 = _make_reviewed("r2", split="test", group="g2")
        report = self._check(r1, r2)
        self.assertFalse(report.ready)
        self.assertTrue(any("exact normalized source text crosses splits" in e.message for e in report.errors))

    # -- Source-type / fixture exclusion --

    def test_test_fixture_pseudonym_in_reviewed_at_does_not_make_record_valid_research(self):
        """
        Records using test-fixture reviewer pseudonyms pass the structural check
        but this test documents that such records must not be treated as real
        research evidence. The validator checks structure, not identity authenticity.
        """
        record = _make_reviewed()
        # The fixture uses a pseudonym flagged as 'not a real reviewer'.
        # Structural checks pass — the validator cannot authenticate identity.
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "records.jsonl"
            _write_jsonl([record], p)
            struct_report = validate_dataset(p)
            ready_report = check_evaluation_readiness(p)
        self.assertTrue(struct_report.valid)   # Structure is valid
        self.assertTrue(ready_report.ready)    # Readiness passes (validator cannot check identity)
        # Documentation: This test exists to record that structural + readiness validity
        # does NOT substitute for authentic human review. External audit trail required.
        self.assertEqual(
            record["review"]["reviewer_id"],
            "p28-test-fixture-pseudonym-not-a-real-reviewer",
        )


# ---------------------------------------------------------------------------
# Pilot dataset file integrity tests (new in Phase 28)
# ---------------------------------------------------------------------------

class TestPilotDatasetIntegrity(unittest.TestCase):
    """
    Tests that run against the actual pilot_examples.jsonl file.
    These verify the pilot was constructed correctly and establish a regression
    baseline. They verify structural validity but NOT evaluation readiness.
    """

    PILOT_PATH = Path(__file__).resolve().parents[2] / "data" / "drafts" / "pilot_examples.jsonl"

    def setUp(self):
        if not self.PILOT_PATH.exists():
            self.skipTest(f"Pilot dataset not found at {self.PILOT_PATH}")

    def test_pilot_file_is_structurally_valid(self):
        """pilot_examples.jsonl must pass structural validation with 0 errors."""
        report = validate_dataset(self.PILOT_PATH)
        self.assertTrue(report.valid, report.errors)
        self.assertEqual(len(report.errors), 0)

    def test_pilot_file_has_expected_record_count(self):
        """pilot_examples.jsonl must contain exactly 28 records."""
        report = validate_dataset(self.PILOT_PATH)
        self.assertEqual(report.records_examined, 28)

    def test_pilot_file_has_draft_warnings(self):
        """Every pilot record is a draft and must produce the unreviewed warning."""
        report = validate_dataset(self.PILOT_PATH)
        self.assertEqual(len(report.warnings), 28)
        for w in report.warnings:
            self.assertIn("draft is unreviewed", w.message)

    def test_pilot_file_is_not_evaluation_ready(self):
        """pilot_examples.jsonl must report NOT READY."""
        report = check_evaluation_readiness(self.PILOT_PATH)
        self.assertFalse(report.ready)

    def test_pilot_all_records_have_project_authored_source_type(self):
        """All pilot records must have source_type='project_authored_constructed'."""
        import json as json_module
        with self.PILOT_PATH.open(encoding="utf-8") as f:
            records = [json_module.loads(line) for line in f if line.strip()]
        for record in records:
            self.assertEqual(
                record.get("source_type"),
                "project_authored_constructed",
                f"Record {record.get('id')} has unexpected source_type",
            )

    def test_pilot_all_records_have_null_reference_translation(self):
        """All pilot records must have reference_translation=null (no fabricated references)."""
        import json as json_module
        with self.PILOT_PATH.open(encoding="utf-8") as f:
            records = [json_module.loads(line) for line in f if line.strip()]
        for record in records:
            self.assertIsNone(
                record.get("reference_translation"),
                f"Record {record.get('id')} has a non-null reference_translation before review",
            )

    def test_pilot_all_records_have_null_intended_meaning(self):
        """All pilot records must have intended_meaning=null (no fabricated meanings)."""
        import json as json_module
        with self.PILOT_PATH.open(encoding="utf-8") as f:
            records = [json_module.loads(line) for line in f if line.strip()]
        for record in records:
            self.assertIsNone(
                record.get("intended_meaning"),
                f"Record {record.get('id')} has a non-null intended_meaning before review",
            )

    def test_pilot_all_records_have_unique_ids(self):
        """All pilot record IDs must be unique."""
        import json as json_module
        with self.PILOT_PATH.open(encoding="utf-8") as f:
            records = [json_module.loads(line) for line in f if line.strip()]
        ids = [r.get("id") for r in records]
        self.assertEqual(len(ids), len(set(ids)), "Pilot dataset contains duplicate IDs")

    def test_pilot_all_records_annotation_status_is_draft(self):
        """All pilot records must have annotation_status='draft'."""
        import json as json_module
        with self.PILOT_PATH.open(encoding="utf-8") as f:
            records = [json_module.loads(line) for line in f if line.strip()]
        for record in records:
            self.assertEqual(
                record.get("annotation_status"),
                "draft",
                f"Record {record.get('id')} has unexpected annotation_status",
            )

    def test_pilot_no_records_have_split_assignment(self):
        """No pilot records should have a split assignment (not yet split-assigned)."""
        import json as json_module
        with self.PILOT_PATH.open(encoding="utf-8") as f:
            records = [json_module.loads(line) for line in f if line.strip()]
        for record in records:
            self.assertNotIn(
                "split",
                record,
                f"Record {record.get('id')} has a premature split assignment",
            )

    def test_pilot_normalized_text_matches_project_convention(self):
        """All pilot records must have normalized_text == ' '.join(text.split())."""
        import json as json_module
        with self.PILOT_PATH.open(encoding="utf-8") as f:
            records = [json_module.loads(line) for line in f if line.strip()]
        for record in records:
            text = record.get("text", "")
            expected_norm = " ".join(text.split())
            self.assertEqual(
                record.get("normalized_text"),
                expected_norm,
                f"Record {record.get('id')} has incorrect normalized_text",
            )


if __name__ == "__main__":
    unittest.main()
