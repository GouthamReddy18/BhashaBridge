import copy
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from app.services.evaluation import evaluate_paired_records
from app.schemas.evaluation import PairedEvaluationArtifact
from app.services.experiment import run_paired_experiment
from app.services.evaluation_readiness import check_evaluation_readiness
from app.services.evaluation_report_validation import validate_evaluation_report
from scripts.validate_evaluation_report import main
from test_evaluation import make_annotation, make_artifact


def make_valid_report(*, include_per_example=True):
    record = make_annotation()
    artifact = make_artifact(record)
    with tempfile.TemporaryDirectory() as directory:
        annotations_path = Path(directory) / "annotations.jsonl"
        annotations_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
        readiness = check_evaluation_readiness(annotations_path)
        report = evaluate_paired_records(
            dataset_label="synthetic-test-fixture-only",
            split="test",
            annotation_rows=[(1, record)],
            readiness=readiness,
            paired_artifacts=[artifact],
            include_per_example=include_per_example,
        )
        return report.model_dump(mode="json")


class EvaluationReportValidationServiceTests(unittest.TestCase):
    def setUp(self):
        self.report = make_valid_report()

    def test_actual_phase_6d2_report_is_valid_and_repeatable(self):
        first = validate_evaluation_report(self.report)
        second = validate_evaluation_report(copy.deepcopy(self.report))
        self.assertEqual(first.status, "VALID")
        self.assertEqual(first.model_dump(mode="json"), second.model_dump(mode="json"))

    def test_validated_report_model_is_accepted(self):
        from app.schemas.evaluation import EvaluationReport
        model = EvaluationReport.model_validate(self.report)
        self.assertEqual(validate_evaluation_report(model).status, "VALID")

    def test_phase_6d2_no_metric_population_report_is_valid(self):
        record = make_annotation()
        result = run_paired_experiment(record["text"], provider=None)
        artifact = PairedEvaluationArtifact(schema_version="1.0", example_id=record["id"], result=result)
        with tempfile.TemporaryDirectory() as directory:
            annotations_path = Path(directory) / "annotations.jsonl"
            annotations_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            readiness = check_evaluation_readiness(annotations_path)
            report = evaluate_paired_records(
                dataset_label="synthetic-test-fixture-only", split="test",
                annotation_rows=[(1, record)], readiness=readiness,
                paired_artifacts=[artifact],
            )
        self.assertEqual(report.evaluation_status, "no_metric_population")
        self.assertEqual(validate_evaluation_report(report).status, "VALID")

    def test_phase_6d2_readiness_blocked_report_is_valid(self):
        record = make_annotation()
        record["annotation_status"] = "draft"
        record["review"] = {"status": "not_reviewed", "notes": "Synthetic test fixture only."}
        record["reference_translation"] = None
        record["intended_meaning"] = None
        record["annotation_provenance"]["fields"] = {}
        with tempfile.TemporaryDirectory() as directory:
            annotations_path = Path(directory) / "annotations.jsonl"
            annotations_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            readiness = check_evaluation_readiness(annotations_path)
            report = evaluate_paired_records(
                dataset_label="synthetic-test-fixture-only", split="test",
                annotation_rows=[(1, record)], readiness=readiness,
                paired_artifacts=[],
            )
        self.assertEqual(report.evaluation_status, "not_evaluated")
        self.assertEqual(validate_evaluation_report(report).status, "VALID")

    def test_optional_metadata_can_be_absent(self):
        value = copy.deepcopy(self.report)
        for name in ("per_example_comparisons", "human_semantic_preservation", "warnings"):
            value.pop(name)
        self.assertEqual(validate_evaluation_report(value).status, "VALID")

    def test_valid_report_with_empty_warning_list(self):
        value = copy.deepcopy(self.report)
        value["warnings"] = []
        self.assertEqual(validate_evaluation_report(value).status, "VALID")

    def test_required_field_and_wrong_types_are_invalid(self):
        missing = copy.deepcopy(self.report)
        missing.pop("split")
        self.assertEqual(validate_evaluation_report(missing).status, "INVALID")
        wrong = copy.deepcopy(self.report)
        wrong["records_discovered"] = "1"
        self.assertEqual(validate_evaluation_report(wrong).status, "INVALID")

    def test_schema_version_and_metric_version_are_unsupported(self):
        value = copy.deepcopy(self.report)
        value["schema_version"] = "2.0"
        self.assertEqual(validate_evaluation_report(value).status, "UNSUPPORTED_VERSION")
        value = copy.deepcopy(self.report)
        value["metric_configuration"]["version"] = "2.0.0"
        self.assertEqual(validate_evaluation_report(value).status, "UNSUPPORTED_VERSION")
        value = copy.deepcopy(self.report)
        value["metric_configuration"]["implementation"] = "other.metrics"
        self.assertEqual(validate_evaluation_report(value).status, "UNSUPPORTED_VERSION")
        unsupported_minimal = {
            "schema_version": "1.0",
            "metric_configuration": {"version": "9.9.9"},
        }
        self.assertEqual(validate_evaluation_report(unsupported_minimal).status, "UNSUPPORTED_VERSION")

    def test_missing_schema_or_metric_configuration_is_invalid(self):
        value = copy.deepcopy(self.report)
        value.pop("schema_version")
        self.assertEqual(validate_evaluation_report(value).status, "INVALID")
        value = copy.deepcopy(self.report)
        value["metric_configuration"].pop("bleu_order")
        self.assertEqual(validate_evaluation_report(value).status, "INVALID")

    def test_boolean_negative_and_nonfinite_counts_or_scores_are_invalid(self):
        for bad in (True, -1):
            value = copy.deepcopy(self.report)
            value["eligible_records"] = bad
            self.assertEqual(validate_evaluation_report(value).status, "INVALID")
        for bad in (float("nan"), float("inf"), float("-inf")):
            value = copy.deepcopy(self.report)
            value["arms"]["direct"]["available_output_population"]["scores"]["bleu"] = bad
            self.assertEqual(validate_evaluation_report(value).status, "INVALID")

    def test_discovered_eligible_excluded_must_reconcile(self):
        value = copy.deepcopy(self.report)
        value["excluded_records"] = 1
        self.assertIn("population_total_mismatch", {item.code for item in validate_evaluation_report(value).diagnostics})

    def test_outcome_and_success_populations_must_reconcile(self):
        value = copy.deepcopy(self.report)
        value["arms"]["direct"]["outcome_counts"]["missing"] = 1
        self.assertIn("outcome_denominator_mismatch", {item.code for item in validate_evaluation_report(value).diagnostics})
        value = copy.deepcopy(self.report)
        value["arms"]["direct"]["available_output_population"]["examples"] = 0
        self.assertIn("success_population_mismatch", {item.code for item in validate_evaluation_report(value).diagnostics})

    def test_matched_pairs_must_be_subset_of_each_arm(self):
        value = copy.deepcopy(self.report)
        value["arms"]["direct"]["available_output_population"]["examples"] = 0
        codes = {item.code for item in validate_evaluation_report(value).diagnostics}
        self.assertIn("matched_exceeds_arm_successes", codes)
        value = copy.deepcopy(self.report)
        value["matched_output_pairs"] = 2
        self.assertIn("matched_population_mismatch", {item.code for item in validate_evaluation_report(value).diagnostics})
        value = copy.deepcopy(self.report)
        value["arms"]["assisted"]["available_output_population"]["examples"] = 0
        self.assertIn("matched_exceeds_arm_successes", {item.code for item in validate_evaluation_report(value).diagnostics})

    def test_zero_populations_require_null_scores_and_differences(self):
        value = copy.deepcopy(self.report)
        value["arms"]["direct"]["available_output_population"]["examples"] = 0
        value["arms"]["direct"]["available_output_population"]["scores"]["bleu"] = None
        self.assertIn("empty_population_has_score", {item.code for item in validate_evaluation_report(value).diagnostics})

    def test_metric_scores_are_bounded_and_metric_configuration_exact(self):
        for metric in ("bleu", "chrf"):
            value = copy.deepcopy(self.report)
            value["arms"]["direct"]["available_output_population"]["scores"][metric] = 100.01
            self.assertIn("score_out_of_range", {item.code for item in validate_evaluation_report(value).diagnostics})
        value = copy.deepcopy(self.report)
        value["metric_configuration"]["bleu_order"] = 3
        self.assertEqual(validate_evaluation_report(value).status, "INVALID")

    def test_paired_differences_are_assisted_minus_direct_with_tolerance(self):
        value = copy.deepcopy(self.report)
        value["paired_aggregate_differences"]["bleu"] += 0.1
        self.assertIn("paired_difference_mismatch", {item.code for item in validate_evaluation_report(value).diagnostics})
        value = copy.deepcopy(self.report)
        value["paired_aggregate_differences"]["bleu"] += 5e-10
        self.assertEqual(validate_evaluation_report(value).status, "VALID")

    def test_status_readiness_and_mock_metadata_contradictions_are_rejected(self):
        value = copy.deepcopy(self.report)
        value["readiness_diagnostic_counts"] = {"provenance": 1}
        self.assertIn("readiness_status_mismatch", {item.code for item in validate_evaluation_report(value).diagnostics})
        value = copy.deepcopy(self.report)
        value["arms"]["direct"]["confirmed_provider_ids"] = ["mock.test"]
        self.assertIn("unsafe_provider_id", {item.code for item in validate_evaluation_report(value).diagnostics})
        value = copy.deepcopy(self.report)
        value["arms"]["direct"]["failure_code_counts"]["mock_provider_test_only"] = 1
        self.assertIn("mock_provider_outcome_mismatch", {item.code for item in validate_evaluation_report(value).diagnostics})
        value = copy.deepcopy(self.report)
        value["human_semantic_preservation"] = {"status": "complete", "rating": 4}
        self.assertIn("human_rating_claim_unsupported", {item.code for item in validate_evaluation_report(value).diagnostics})

    def test_per_example_diagnostics_must_be_unique_complete_and_consistent(self):
        value = copy.deepcopy(self.report)
        value["per_example_comparisons"].append(copy.deepcopy(value["per_example_comparisons"][0]))
        codes = {item.code for item in validate_evaluation_report(value).diagnostics}
        self.assertIn("duplicate_per_example_id", codes)
        self.assertIn("partial_per_example_diagnostics", codes)
        value = copy.deepcopy(self.report)
        value["per_example_comparisons"][0]["bleu_assisted_minus_direct"] += 1
        self.assertIn("per_example_difference_mismatch", {item.code for item in validate_evaluation_report(value).diagnostics})
        value = copy.deepcopy(self.report)
        value["per_example_order_counts"]["bleu"]["higher"] = 1
        value["per_example_order_counts"]["bleu"]["equal"] = 0
        self.assertIn("per_example_relation_mismatch", {item.code for item in validate_evaluation_report(value).diagnostics})

    def test_diagnostics_are_sanitized_and_sorted(self):
        value = copy.deepcopy(self.report)
        value["unexpected_secret_field"] = "sk-secret-do-not-print"
        value["api-key-material"] = "hidden-value"
        result = validate_evaluation_report(value)
        self.assertEqual(result.status, "INVALID")
        locations = [item.location for item in result.diagnostics]
        self.assertEqual(locations, sorted(locations))
        self.assertNotIn("sk-secret-do-not-print", json.dumps(result.model_dump(mode="json")))
        self.assertNotIn("api-key-material", json.dumps(result.model_dump(mode="json")))


class EvaluationReportValidationCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root / "report.json"
        self.report = make_valid_report()
        self.path.write_text(json.dumps(self.report, sort_keys=True), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_help_is_available(self):
        output = StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as caught:
            main(["--help"])
        self.assertEqual(caught.exception.code, 0)
        self.assertIn("report", output.getvalue())

    def test_valid_report_returns_zero_and_does_not_mutate_input(self):
        before = self.path.read_bytes()
        output = StringIO()
        with redirect_stdout(output):
            code = main([str(self.path)])
        self.assertEqual(code, 0)
        self.assertIn("Report validation: VALID", output.getvalue())
        self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_report_returns_one_with_deterministic_sanitized_diagnostics(self):
        invalid = copy.deepcopy(self.report)
        invalid["unexpected"] = "private-secret-value"
        self.path.write_text(json.dumps(invalid), encoding="utf-8")
        outputs = []
        codes = []
        for _ in range(2):
            output = StringIO()
            with redirect_stdout(output):
                codes.append(main([str(self.path)]))
            outputs.append(output.getvalue())
        self.assertEqual(codes, [1, 1])
        self.assertEqual(outputs[0], outputs[1])
        self.assertNotIn("private-secret-value", outputs[0])

    def test_unsupported_version_returns_two(self):
        invalid = copy.deepcopy(self.report)
        invalid["schema_version"] = "99.0"
        self.path.write_text(json.dumps(invalid), encoding="utf-8")
        with redirect_stdout(StringIO()):
            self.assertEqual(main([str(self.path)]), 2)

    def test_malformed_or_nonstandard_json_returns_one(self):
        for content in ("{bad", '{"x":1,"x":2}', '{"value":NaN}'):
            self.path.write_text(content, encoding="utf-8")
            with redirect_stdout(StringIO()):
                self.assertEqual(main([str(self.path)]), 1)

    def test_missing_file_and_directory_return_two_without_traceback(self):
        stderr = StringIO()
        with redirect_stderr(stderr):
            self.assertEqual(main([str(self.root / "missing.json")]), 2)
            self.assertEqual(main([str(self.root)]), 2)
        self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
