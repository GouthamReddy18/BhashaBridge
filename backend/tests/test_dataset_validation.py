import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from app.services.dataset_validation import validate_dataset
from app.services.preprocessing import normalize_whitespace
from app.services.tokenization import tokenize
from scripts.validate_dataset import main


def make_record(text="hello there", record_id="unit-001"):
    normalized = normalize_whitespace(text)
    return {
        "annotation_version": "1.0",
        "id": record_id,
        "text": text,
        "normalized_text": normalized,
        "source_type": "synthetic_illustrative",
        "annotation_status": "draft",
        "annotation_provenance": {"method": "test_fixture", "details": "Unreviewed test fixture."},
        "tokens": [
            {"index": token.index, "surface": token.text, "start": token.start,
             "end": token.end, "language_label": "UNKNOWN"}
            for token in tokenize(normalized)
        ],
        "romanized_interpretation": None,
        "telugu_script_equivalent": None,
        "ambiguity": None,
        "reference_translation": None,
    }


class DatasetValidationTests(unittest.TestCase):
    def validate_records(self, *records):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.jsonl"
            path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records), encoding="utf-8")
            return validate_dataset(path)

    def test_valid_illustrative_draft_record_has_only_nonblocking_warning(self):
        report = self.validate_records(make_record())
        self.assertTrue(report.valid)
        self.assertEqual(report.records_examined, 1)
        self.assertEqual(report.errors, [])
        self.assertEqual(len(report.warnings), 1)

    def test_malformed_jsonl_reports_line_number(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.jsonl"
            path.write_text("\n{broken\n", encoding="utf-8")
            report = validate_dataset(path)
        self.assertEqual(report.errors[0].line, 2)
        self.assertIn("malformed JSON", report.errors[0].message)

    def test_missing_required_fields(self):
        report = self.validate_records({"id": "missing"})
        self.assertTrue(any("missing required field: text" in e.message for e in report.errors))

    def test_duplicate_record_ids(self):
        report = self.validate_records(make_record(record_id="same"), make_record(record_id="same"))
        self.assertTrue(any("duplicate record id" in e.message for e in report.errors))

    def test_unsupported_language_label(self):
        record = make_record(); record["tokens"][0]["language_label"] = "MARS"
        self.assertTrue(any("unsupported language_label" in e.message for e in self.validate_records(record).errors))

    def test_incorrect_token_index(self):
        record = make_record(); record["tokens"][0]["index"] = 8
        self.assertTrue(any("index must equal" in e.message for e in self.validate_records(record).errors))

    def test_incorrect_token_offset(self):
        record = make_record(); record["tokens"][0]["start"] = 1
        self.assertTrue(any("surface does not match" in e.message or "tokenizer boundaries" in e.message for e in self.validate_records(record).errors))

    def test_incorrect_token_surface(self):
        record = make_record(); record["tokens"][0]["surface"] = "wrong"
        self.assertTrue(any("surface does not match" in e.message for e in self.validate_records(record).errors))

    def test_overlapping_token_spans(self):
        record = make_record("a b")
        record["tokens"][1]["start"] = 0
        record["tokens"][1]["end"] = 1
        self.assertTrue(any("overlaps or is out of order" in e.message for e in self.validate_records(record).errors))

    def test_empty_text_is_invalid(self):
        record = make_record("hello"); record["text"] = "  "; record["normalized_text"] = ""
        self.assertTrue(any("text must be a non-empty string" in e.message for e in self.validate_records(record).errors))

    def test_inconsistent_normalized_text(self):
        record = make_record(); record["normalized_text"] = "different"
        self.assertTrue(any("does not match project whitespace" in e.message for e in self.validate_records(record).errors))

    def test_invalid_annotation_status_and_version(self):
        record = make_record(); record["annotation_status"] = ["draft"]; record["annotation_version"] = "9.9"
        messages = [e.message for e in self.validate_records(record).errors]
        self.assertTrue(any("annotation_status" in m for m in messages))
        self.assertTrue(any("unsupported annotation_version" in m for m in messages))

    def test_missing_provenance_and_contradictory_review_metadata(self):
        record = make_record(); record["annotation_provenance"] = {"method": "human_review"}
        record["review"] = {"status": "reviewed", "reviewer_id": "", "reviewed_at": "not-a-date"}
        messages = [e.message for e in self.validate_records(record).errors]
        self.assertTrue(any("annotation_provenance.details" in m for m in messages))
        self.assertTrue(any("review.status conflicts" in m for m in messages))
        self.assertTrue(any("require supplied reviewer_id" in m for m in messages))

    def ambiguity(self, status, selected):
        return {"status": status, "candidates": [
            {"candidate_id": "sense_a", "meaning": "illustrative A", "source": "test fixture"},
            {"candidate_id": "sense_b", "meaning": "illustrative B", "source": "test fixture"},
        ], "selected_candidate": selected, "evidence": "test only", "rule_id": "test.fixture"}

    def test_selected_ambiguity_meaning_must_be_listed(self):
        record = make_record(); record["ambiguity"] = self.ambiguity("resolved", "not_listed")
        self.assertTrue(any("listed candidate_id" in e.message for e in self.validate_records(record).errors))

    def test_abstained_ambiguity_must_not_select_meaning(self):
        record = make_record(); record["ambiguity"] = self.ambiguity("abstained", "sense_a")
        self.assertTrue(any("must not select" in e.message for e in self.validate_records(record).errors))

    def test_invalid_reference_translation_type(self):
        record = make_record(); record["reference_translation"] = {"made_up": True}
        self.assertTrue(any("reference_translation must be a string or null" in e.message for e in self.validate_records(record).errors))

    def test_astral_unicode_offsets_follow_python_code_points(self):
        record = make_record(chr(0x1f600) + " hello")
        report = self.validate_records(record)
        self.assertTrue(report.valid, report.errors)
        self.assertEqual(record["tokens"][1]["start"], 2)
        self.assertEqual(record["normalized_text"][2:7], "hello")

    def test_missing_optional_linguistic_fields_are_valid(self):
        record = make_record()
        for field in ("romanized_interpretation", "telugu_script_equivalent", "ambiguity", "reference_translation"):
            record.pop(field, None)
        self.assertTrue(self.validate_records(record).valid)

    def test_draft_does_not_require_fabricated_reviewer_metadata(self):
        record = make_record()
        self.assertNotIn("review", record)
        self.assertTrue(self.validate_records(record).valid)

    def test_reviewed_record_requires_consistent_reviewer_metadata(self):
        record = make_record(); record["annotation_status"] = "reviewed"
        record["review"] = {"status": "reviewed", "reviewer_id": "reviewer-pseudonym", "reviewed_at": "2026-01-10"}
        self.assertTrue(self.validate_records(record).valid)

    def test_malformed_json_types_return_validation_errors_not_exceptions(self):
        record = make_record(); record["tokens"][0]["language_label"] = []
        record["ambiguity"] = {"status": [], "candidates": [], "selected_candidate": [], "evidence": "x", "rule_id": "x"}
        record["review"] = {"status": [], "reviewer_id": None, "reviewed_at": None}
        report = self.validate_records(record)
        self.assertFalse(report.valid)

    def test_cli_success_and_failure_exit_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            valid = Path(directory) / "valid.jsonl"
            valid.write_text(json.dumps(make_record()) + "\n", encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(main([str(valid)]), 0)
            self.assertIn("Records examined: 1", output.getvalue())
            with redirect_stdout(StringIO()):
                self.assertEqual(main([str(Path(directory) / "missing.jsonl")]), 1)


if __name__ == "__main__":
    unittest.main()
