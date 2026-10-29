import csv
import json
import tempfile
import unittest
from pathlib import Path

from app.services.annotation_import import import_reviewer_annotations, write_reviewer_template


class TestAnnotationImport(unittest.TestCase):
    def test_reviewer_template_contains_required_columns_and_prompt_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            draft_path = Path(__file__).resolve().parents[2] / "data" / "drafts" / "pilot_examples.jsonl"
            out_path = Path(tmpdir) / "review_template.csv"
            result_path = write_reviewer_template(draft_path, out_path)

            self.assertTrue(result_path.exists())
            with result_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertGreater(len(rows), 0)
            self.assertEqual(rows[0]["example_id"], "pilot-001")
            self.assertEqual(rows[0]["source_text_confirmation"], "nenu office ki veltunna")
            self.assertEqual(rows[0]["intended_meaning"], "")
            self.assertEqual(rows[0]["reviewer_id"], "")

    def test_import_rejects_duplicate_and_unknown_example_ids(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            draft_path = Path(__file__).resolve().parents[2] / "data" / "drafts" / "pilot_examples.jsonl"
            csv_path = Path(tmpdir) / "reviewer_submission.csv"
            csv_path.write_text(
                "example_id,source_text_confirmation,intended_meaning,reference_translation,ambiguity_status,reviewer_notes,reviewer_id,language_competency_declaration,guideline_version,saw_system_outputs,independence_declaration\n"
                "pilot-001,nenu office ki veltunna,The speaker is going to the office.,I am going to the office.,none,Looks fine,reviewer-01,yes,1.0,no,yes\n"
                "pilot-001,nenu office ki veltunna,The speaker is going to the office.,I am going to the office.,none,duplicate row,reviewer-01,yes,1.0,no,yes\n"
                "pilot-999,nenu office ki veltunna,Unknown ID,Unknown ID,none,No such record,reviewer-01,yes,1.0,no,yes\n",
                encoding="utf-8",
            )

            report = import_reviewer_annotations(draft_path, csv_path)
            self.assertFalse(report.valid)
            self.assertTrue(any("duplicate example_id" in issue.message for issue in report.errors))
            self.assertTrue(any("unknown example_id" in issue.message for issue in report.errors))


if __name__ == "__main__":
    unittest.main()
