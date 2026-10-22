import copy
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from app.services.evaluation_readiness import check_evaluation_readiness
from app.services.preprocessing import normalize_whitespace
from app.services.tokenization import tokenize
from scripts.check_evaluation_readiness import main


def make_record(record_id="fixture-001", text="nenu college", split="test", group="group-1"):
    normalized = normalize_whitespace(text)
    tokens = []
    for token in tokenize(normalized):
        label = "TELUGU_ROMANIZED" if token.text == "nenu" else "ENGLISH"
        tokens.append({
            "index": token.index,
            "surface": token.text,
            "start": token.start,
            "end": token.end,
            "language_label": label,
        })
    return {
        "annotation_version": "1.0",
        "id": record_id,
        "text": text,
        "normalized_text": normalized,
        "source_type": "synthetic_test_fixture",
        "annotation_status": "reviewed",
        "annotation_provenance": {
            "method": "test_fixture_only",
            "details": "Synthetic unit-test metadata; not a real reviewed record.",
            "origin": "human",
            "fields": {
                "reference_translation": {
                    "origin": "human",
                    "review_status": "reviewed",
                    "details": "Synthetic test fixture only.",
                    "source_reference": "test-fixture-reference",
                },
                "intended_meaning": {
                    "origin": "human",
                    "review_status": "reviewed",
                    "details": "Synthetic test fixture only.",
                    "source_reference": "test-fixture-meaning",
                },
            },
        },
        "tokens": tokens,
        "reference_translation": "I went to college.",
        "intended_meaning": "The speaker went to college.",
        "review": {
            "status": "reviewed",
            "reviewer_id": "test-fixture-pseudonym-not-a-real-reviewer",
            "reviewed_at": "2026-01-10",
            "notes": "Synthetic test fixture only.",
        },
        "split": split,
        "split_group": group,
    }


class EvaluationReadinessTests(unittest.TestCase):
    def validate_records(self, *records):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.jsonl"
            path.write_text(
                "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
                encoding="utf-8",
            )
            return check_evaluation_readiness(path)

    def test_valid_structural_draft_is_not_evaluation_ready(self):
        record = make_record()
        record["annotation_status"] = "draft"
        record.pop("review")
        record["reference_translation"] = None
        record["intended_meaning"] = None
        record["annotation_provenance"]["fields"] = {}
        report = self.validate_records(record)
        self.assertFalse(report.ready)
        messages = [issue.message for issue in report.errors]
        self.assertIn("record is not reviewed and is ineligible for benchmark use", messages)
        self.assertIn("human-reviewed English reference_translation is required", messages)

    def test_missing_reference_translation_is_blocking(self):
        record = make_record()
        record["reference_translation"] = None
        del record["annotation_provenance"]["fields"]["reference_translation"]
        report = self.validate_records(record)
        self.assertTrue(any("reference_translation is required" in issue.message for issue in report.errors))

    def test_missing_review_metadata_is_blocking(self):
        record = make_record()
        record.pop("review")
        report = self.validate_records(record)
        self.assertTrue(any("completed review metadata is required" in issue.message for issue in report.errors))

    def test_invalid_provenance_is_blocking(self):
        record = make_record()
        record["annotation_provenance"]["origin"] = "invented"
        report = self.validate_records(record)
        self.assertTrue(any("origin must be human" in issue.message for issue in report.errors))
        self.assertFalse(report.ready)

    def test_duplicate_ids_are_reported_by_structural_validation(self):
        report = self.validate_records(make_record("same"), make_record("same", text="nenu office", group="group-2"))
        self.assertTrue(any("duplicate record id: same" in issue.message for issue in report.errors))

    def test_duplicate_source_text_across_splits_is_blocking(self):
        first = make_record("train-row", split="train", group="train-group")
        second = make_record("test-row", split="test", group="test-group")
        report = self.validate_records(first, second)
        self.assertTrue(any("exact normalized source text crosses splits" in issue.message for issue in report.errors))

    def test_duplicate_source_text_within_split_is_blocking(self):
        first = make_record("first-row", split="test", group="shared-family")
        second = make_record("second-row", split="test", group="shared-family")
        report = self.validate_records(first, second)
        self.assertTrue(any("duplicate normalized source text within split 'test'" in issue.message for issue in report.errors))

    def test_split_group_cannot_cross_splits(self):
        first = make_record("train-row", split="train", group="shared-family")
        second = make_record("test-row", text="nenu office", split="test", group="shared-family")
        report = self.validate_records(first, second)
        self.assertTrue(any("split_group 'shared-family' crosses splits" in issue.message for issue in report.errors))

    def test_missing_split_assignment_is_blocking(self):
        record = make_record()
        record.pop("split")
        report = self.validate_records(record)
        self.assertTrue(any("valid split assignment" in issue.message for issue in report.errors))

    def test_unsupported_split_value_is_blocking(self):
        record = make_record(split="holdout")
        report = self.validate_records(record)
        self.assertTrue(any("split must be train, validation, or test" in issue.message for issue in report.errors))

    def test_malformed_split_type_is_reported_without_raising(self):
        record = make_record(split=[])
        report = self.validate_records(record)
        self.assertTrue(any("split must be train, validation, or test" in issue.message for issue in report.errors))

    def test_missing_required_intended_meaning_is_blocking(self):
        record = make_record()
        record["intended_meaning"] = None
        del record["annotation_provenance"]["fields"]["intended_meaning"]
        report = self.validate_records(record)
        self.assertTrue(any("reviewed intended_meaning is required" in issue.message for issue in report.errors))

    def test_test_split_requires_romanized_telugu_and_english(self):
        record = make_record(text="nenu", split="test")
        report = self.validate_records(record)
        self.assertTrue(any("TELUGU_ROMANIZED and ENGLISH tokens" in issue.message for issue in report.errors))

    def test_structurally_invalid_jsonl_is_blocking_with_line_number(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "malformed.jsonl"
            path.write_text("{broken\n", encoding="utf-8")
            report = check_evaluation_readiness(path)
        self.assertFalse(report.ready)
        self.assertTrue(any(issue.line == 1 and "malformed JSON" in issue.message for issue in report.errors))

    def test_nonexistent_dataset_reports_only_actionable_path_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.jsonl"
            first = check_evaluation_readiness(path)
            second = check_evaluation_readiness(path)
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main([str(path)])

        self.assertFalse(first.ready)
        self.assertEqual(first.errors, second.errors)
        self.assertEqual(len(first.errors), 1)
        self.assertIn("cannot read dataset:", first.errors[0].message)
        self.assertNotIn("dataset contains no records", first.errors[0].message)
        self.assertEqual(exit_code, 1)
        self.assertIn("Readiness: NOT READY", output.getvalue())
        self.assertIn("Errors: 1", output.getvalue())
        self.assertNotIn("dataset contains no records", output.getvalue())

    def test_directory_path_reports_read_error_without_empty_dataset_error(self):
        # Opening a directory as a UTF-8 text file fails consistently across
        # supported platforms, unlike relying on filesystem permission bits.
        with tempfile.TemporaryDirectory() as directory:
            report = check_evaluation_readiness(Path(directory))
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main([directory])

        self.assertFalse(report.ready)
        self.assertEqual(len(report.errors), 1)
        self.assertIn("cannot read dataset:", report.errors[0].message)
        self.assertNotIn("dataset contains no records", output.getvalue())
        self.assertEqual(exit_code, 1)

    def test_readable_empty_dataset_remains_not_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.jsonl"
            path.write_text("", encoding="utf-8")
            report = check_evaluation_readiness(path)
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main([str(path)])

        self.assertFalse(report.ready)
        self.assertEqual(len(report.errors), 1)
        self.assertEqual(report.errors[0].message, "dataset contains no records")
        self.assertEqual(exit_code, 1)
        self.assertIn("dataset contains no records", output.getvalue())

    def test_structural_errors_remain_visible_in_readiness_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "malformed.jsonl"
            path.write_text("{broken\n", encoding="utf-8")
            report = check_evaluation_readiness(path)
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main([str(path)])

        self.assertFalse(report.ready)
        self.assertTrue(any("malformed JSON" in issue.message for issue in report.errors))
        self.assertEqual(exit_code, 1)
        self.assertIn("malformed JSON", output.getvalue())

    def test_explicit_synthetic_review_fixture_exercises_ready_path_only(self):
        report = self.validate_records(make_record())
        self.assertTrue(report.ready, report.errors)
        self.assertEqual(report.records_examined, 1)

    def test_checker_does_not_mutate_input_record(self):
        record = make_record()
        original = copy.deepcopy(record)
        self.validate_records(record)
        self.assertEqual(record, original)

    def test_diagnostics_are_deterministic(self):
        record = make_record()
        record["split"] = "bad"
        first = self.validate_records(record)
        second = self.validate_records(record)
        self.assertEqual(first.errors, second.errors)
        self.assertEqual(first.warnings, second.warnings)

    def test_cli_exit_status_for_ready_and_not_ready_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ready_path = root / "ready.jsonl"
            ready_path.write_text(json.dumps(make_record()) + "\n", encoding="utf-8")
            draft = make_record()
            draft["annotation_status"] = "draft"
            draft.pop("review")
            not_ready_path = root / "draft.jsonl"
            not_ready_path.write_text(json.dumps(draft) + "\n", encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                ready_code = main([str(ready_path)])
                not_ready_code = main([str(not_ready_path)])
        self.assertEqual(ready_code, 0)
        self.assertEqual(not_ready_code, 1)
        self.assertIn("Readiness: NOT READY", output.getvalue())


if __name__ == "__main__":
    unittest.main()
