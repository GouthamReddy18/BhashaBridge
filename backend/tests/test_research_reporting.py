import copy
import json
import tempfile
import unittest
from pathlib import Path

from app.services.research_reporting import (
    ResearchReportError, build_research_report, build_research_report_file,
)
from test_evaluation_report_validation import make_valid_report


def human_summary(evaluation):
    arms = {}
    for arm in ("direct", "assisted"):
        available = evaluation["arms"][arm]["available_output_example_ids"]
        eligible = evaluation["eligible_example_ids"]
        arms[arm] = {
            "available_output_examples": len(available),
            "available_output_example_ids": available,
            "unavailable_output_example_ids": sorted(set(eligible) - set(available)),
            "unavailable_output_examples": len(eligible) - len(available),
            "rated_examples_with_required_reviewers": len(available),
            "rated_example_ids": available,
            "missing_or_insufficiently_reviewed_examples": 0,
            "pending_judgments": 0,
            "completed_judgments": len(available),
            "rating_distribution": {"0": 0, "1": 0, "2": 1, "3": 0, "4": 0},
        }
    return {
        "schema_version": "1.0",
        "rubric_version": "semantic-preservation-0-4.v1",
        "dataset_label": evaluation["dataset_label"],
        "split": evaluation["split"],
        "minimum_independent_reviewers": 1,
        "blinded_presentation": True,
        "arms": arms,
        "inter_annotator_agreement": {"status": "not_calculated"},
    }


class ResearchReportingTests(unittest.TestCase):
    def setUp(self):
        self.evaluation = make_valid_report()

    def test_builds_descriptive_report_from_valid_evaluation(self):
        report = build_research_report(self.evaluation)
        self.assertEqual(report["report_status"], "descriptive_metrics_available")
        self.assertEqual(report["evaluation_validation_status"], "VALID")
        self.assertIsNone(report["human_rating_summary"])
        self.assertTrue(any("No statistical significance" in item for item in report["limitations"]))

    def test_accepts_human_ratings_only_when_dataset_and_id_denominators_match(self):
        summary = human_summary(self.evaluation)
        report = build_research_report(self.evaluation, summary)
        self.assertEqual(report["human_rating_summary"], summary)
        mismatch = copy.deepcopy(summary)
        mismatch["arms"]["direct"]["available_output_example_ids"] = ["different-id"]
        with self.assertRaisesRegex(ResearchReportError, "available IDs"):
            build_research_report(self.evaluation, mismatch)

    def test_rejects_invalid_or_ineligible_evaluation_report(self):
        value = copy.deepcopy(self.evaluation)
        value["arms"]["direct"]["available_output_population"]["examples"] += 1
        with self.assertRaisesRegex(ResearchReportError, "integrity"):
            build_research_report(value)
        no_eligible = copy.deepcopy(self.evaluation)
        no_eligible["eligible_records"] = 0
        with self.assertRaises(ResearchReportError):
            build_research_report(no_eligible)

    def test_rejects_rating_report_with_wrong_dataset_or_agreement_claim(self):
        summary = human_summary(self.evaluation)
        summary["dataset_label"] = "different-dataset"
        with self.assertRaisesRegex(ResearchReportError, "does not match"):
            build_research_report(self.evaluation, summary)
        summary = human_summary(self.evaluation)
        summary["inter_annotator_agreement"] = {"status": "calculated", "statistic": "kappa"}
        with self.assertRaisesRegex(ResearchReportError, "agreement"):
            build_research_report(self.evaluation, summary)

    def test_file_writer_is_deterministic_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "evaluation.json", root / "research.json"
            source.write_text(json.dumps(self.evaluation), encoding="utf-8")
            build_research_report_file(source, output)
            first = output.read_bytes()
            with self.assertRaisesRegex(ResearchReportError, "already exists"):
                build_research_report_file(source, output)
            self.assertEqual(output.read_bytes(), first)


if __name__ == "__main__":
    unittest.main()
