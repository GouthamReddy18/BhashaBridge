import copy
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from pydantic import ValidationError

from app.schemas.evaluation import MetricConfiguration, PairedEvaluationArtifact
from app.schemas.experiment import ExperimentConfiguration
from app.services.evaluation import evaluate_paired_records
from app.services.evaluation_metrics import corpus_bleu, corpus_chrf
from app.services.evaluation_readiness import check_evaluation_readiness
from app.services.experiment import run_paired_experiment
from app.services.preprocessing import normalize_whitespace
from app.services.tokenization import tokenize
from app.services.translation import MockTranslationProvider
from scripts.evaluate_paired_experiment import main


def make_annotation(example_id="fixture-001", text="nenu college", split="test", group="family-1"):
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
        "id": example_id,
        "text": text,
        "normalized_text": normalized,
        "source_type": "synthetic_test_fixture_only",
        "annotation_status": "reviewed",
        "annotation_provenance": {
            "method": "unit_test_fixture",
            "details": "Synthetic fixture only; no real review or source is asserted.",
            "origin": "human",
            "fields": {
                "reference_translation": {
                    "origin": "human", "review_status": "reviewed",
                    "details": "Synthetic test fixture only.", "source_reference": "test-only-ref",
                },
                "intended_meaning": {
                    "origin": "human", "review_status": "reviewed",
                    "details": "Synthetic test fixture only.", "source_reference": "test-only-meaning",
                },
            },
        },
        "tokens": tokens,
        "reference_translation": "I went to college.",
        "intended_meaning": "The speaker went to college.",
        "review": {
            "status": "reviewed", "reviewer_id": "synthetic-test-fixture",
            "reviewed_at": "2026-01-10", "notes": "Not a real review.",
        },
        "split": split,
        "split_group": group,
    }


class MappingProvider:
    provider_id = "test.provider"

    def __init__(self, outputs=None, error=False):
        self.outputs = outputs or {}
        self.error = error

    def translate(self, request):
        if self.error:
            raise RuntimeError("synthetic secret-bearing provider exception")
        from app.services.translation import ProviderTranslation
        return ProviderTranslation(self.outputs.get(request.text, "A synthetic test output."))


def make_artifact(record, direct_output="I went to college.", assisted_output="I went to college.", order="direct_first", error_arms=()):
    normalized = normalize_whitespace(record["text"])
    provider = MappingProvider({
        record["text"]: direct_output,
        normalized: assisted_output,
    })
    if error_arms:
        provider = SelectiveFailureProvider(
            outputs={record["text"]: direct_output, normalized: assisted_output},
            failure_inputs={record["text"] if arm == "direct" else normalized for arm in error_arms},
        )
    result = run_paired_experiment(
        record["text"], provider=provider,
        configuration=ExperimentConfiguration(execution_order=order),
    )
    return PairedEvaluationArtifact(schema_version="1.0", example_id=record["id"], result=result)


class SelectiveFailureProvider(MappingProvider):
    def __init__(self, outputs, failure_inputs):
        super().__init__(outputs)
        self.failure_inputs = failure_inputs

    def translate(self, request):
        if request.text in self.failure_inputs:
            raise RuntimeError("synthetic secret-bearing provider exception")
        from app.services.translation import ProviderTranslation
        return ProviderTranslation(self.outputs.get(request.text, "A synthetic test output."))


class MetadataFailureProvider:
    @property
    def provider_id(self):
        raise RuntimeError("synthetic provider metadata failure")

    def translate(self, request):
        raise AssertionError("translation must not be invoked")


class InvalidOutputProvider:
    provider_id = "test.provider"

    def translate(self, request):
        return object()


class EvaluationMetricTests(unittest.TestCase):
    def test_known_bleu_example_and_identical_inputs(self):
        score = corpus_bleu(["the cat is on the mat"], ["the cat is on the mat"])
        self.assertEqual(score, 100.0)
        changed = corpus_bleu(["the cat is on the mat"], ["the cat is on mat"])
        self.assertAlmostEqual(changed, 57.8930067467, places=9)

    def test_known_chrf_example_and_identical_inputs(self):
        self.assertEqual(corpus_chrf(["café, తెలుగు!"], ["café, తెలుగు!"]), 100.0)
        changed = corpus_chrf(["abcd"], ["abce"])
        self.assertAlmostEqual(changed, 47.9166666667, places=8)

    def test_empty_corpus_has_no_score_and_blank_rows_are_rejected(self):
        self.assertIsNone(corpus_bleu([], []))
        self.assertIsNone(corpus_chrf([], []))
        for metric in (corpus_bleu, corpus_chrf):
            with self.subTest(metric=metric.__name__), self.assertRaises(ValueError):
                metric(["reference"], ["   "])
            with self.subTest(metric=metric.__name__), self.assertRaises(ValueError):
                metric(["  "], ["hypothesis"])
            with self.subTest(metric=metric.__name__), self.assertRaises(ValueError):
                metric(["reference"], [])

    def test_unicode_punctuation_normalization_and_determinism(self):
        refs = ["  café,\tతెలుగు!  "]
        hyps = ["cafe\u0301, తెలుగు!"]
        first = (corpus_bleu(refs, hyps), corpus_chrf(refs, hyps))
        second = (corpus_bleu(refs, hyps), corpus_chrf(refs, hyps))
        self.assertEqual(first, second)
        self.assertEqual(first, (100.0, 100.0))

    def test_invalid_metric_configuration_is_rejected(self):
        with self.assertRaises(ValidationError):
            MetricConfiguration(bleu_order=3)
        with self.assertRaises(ValidationError):
            MetricConfiguration(chrf_word_order=2)


class EvaluationServiceTests(unittest.TestCase):
    def evaluate(self, records, artifacts, split="test", include_per_example=False):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "annotations.jsonl"
            path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
            readiness = check_evaluation_readiness(path)
            rows = [(index, row) for index, row in enumerate(records, start=1)]
            return evaluate_paired_records(
                dataset_label="test-only-fixture", split=split,
                annotation_rows=rows, readiness=readiness, paired_artifacts=artifacts,
                include_per_example=include_per_example,
            )

    def test_reviewed_fixture_is_eligible_only_as_test_data(self):
        record = make_annotation()
        artifact = make_artifact(record)
        report = self.evaluate([record], [artifact])
        self.assertEqual(report.evaluation_status, "evaluated")
        self.assertEqual(report.records_discovered, 1)
        self.assertEqual(report.eligible_records, 1)
        self.assertEqual(report.matched_output_pairs, 1)
        self.assertEqual(report.arms["direct"].available_output_population.examples, 1)

    def test_draft_and_missing_reference_are_blocking_without_scores(self):
        record = make_annotation()
        record["annotation_status"] = "draft"
        record["review"] = {"status": "not_reviewed"}
        record["reference_translation"] = None
        record["intended_meaning"] = None
        record["annotation_provenance"]["fields"] = {}
        report = self.evaluate([record], [make_artifact(record)])
        self.assertEqual(report.evaluation_status, "not_evaluated")
        self.assertEqual(report.eligible_records, 0)
        self.assertEqual(report.excluded_records, 1)
        self.assertIn("review_metadata", report.readiness_diagnostic_counts)
        self.assertIsNone(report.arms["direct"].available_output_population.scores.bleu)

    def test_missing_provenance_and_invalid_split_group_are_blocking(self):
        record = make_annotation()
        del record["annotation_provenance"]["fields"]["reference_translation"]
        record["split_group"] = "  "
        report = self.evaluate([record], [make_artifact(record)])
        self.assertEqual(report.evaluation_status, "not_evaluated")
        self.assertIn("reference_translation", report.readiness_diagnostic_counts)
        self.assertIn("split_or_leakage", report.readiness_diagnostic_counts)

    def test_missing_reference_and_cross_split_group_are_blocking(self):
        missing = make_annotation("missing-ref")
        missing["reference_translation"] = None
        del missing["annotation_provenance"]["fields"]["reference_translation"]
        first = make_annotation("test-member", "nenu college", split="test", group="shared-family")
        second = make_annotation("train-member", "nenu office", split="train", group="shared-family")
        report = self.evaluate([missing, first, second], [make_artifact(missing), make_artifact(first)])
        self.assertEqual(report.evaluation_status, "not_evaluated")
        self.assertIn("reference_translation", report.readiness_diagnostic_counts)
        self.assertIn("split_or_leakage", report.readiness_diagnostic_counts)
        self.assertEqual(report.eligible_records, 0)

    def test_unavailable_provider_outcomes_are_counted_and_not_scored(self):
        record = make_annotation()
        result = run_paired_experiment(record["text"], provider=None)
        artifact = PairedEvaluationArtifact(schema_version="1.0", example_id=record["id"], result=result)
        report = self.evaluate([record], [artifact])
        for arm in ("direct", "assisted"):
            self.assertEqual(report.arms[arm].outcome_counts["unavailable"], 1)
            self.assertEqual(report.arms[arm].available_output_population.examples, 0)
        self.assertEqual(report.evaluation_status, "no_metric_population")

    def test_mock_provider_outputs_are_never_scored_as_evidence(self):
        record = make_annotation()
        result = run_paired_experiment(record["text"], provider=MockTranslationProvider())
        artifact = PairedEvaluationArtifact(schema_version="1.0", example_id=record["id"], result=result)
        report = self.evaluate([record], [artifact])
        self.assertEqual(report.evaluation_status, "no_metric_population")
        for arm in ("direct", "assisted"):
            self.assertEqual(report.arms[arm].outcome_counts["invalid"], 1)
            self.assertEqual(report.arms[arm].failure_code_counts["mock_provider_test_only"], 1)
            self.assertEqual(report.arms[arm].available_output_population.examples, 0)

    def test_failed_arm_remains_failure_while_other_arm_is_scored(self):
        record = make_annotation(text=" nenu   college ")
        artifact = make_artifact(record, error_arms=("direct",), order="assisted_first")
        report = self.evaluate([record], [artifact])
        self.assertEqual(report.arms["direct"].outcome_counts["failed"], 1)
        self.assertEqual(report.arms["direct"].failure_code_counts["provider_error"], 1)
        self.assertEqual(report.arms["assisted"].outcome_counts["success"], 1)
        self.assertEqual(report.arms["direct"].available_output_population.examples, 0)
        self.assertEqual(report.arms["assisted"].available_output_population.examples, 1)
        self.assertEqual(report.matched_output_pairs, 0)
        self.assertIsNone(report.paired_aggregate_differences.bleu)
        self.assertEqual(report.invocation_trace_counts["assisted,direct"], 1)
        self.assertNotIn("synthetic secret-bearing", json.dumps(report.model_dump(mode="json")))

    def test_both_arms_failed_are_not_fabricated_as_scores(self):
        record = make_annotation(text=" nenu   college ")
        artifact = make_artifact(record, error_arms=("direct", "assisted"))
        report = self.evaluate([record], [artifact])
        self.assertEqual(report.arms["direct"].outcome_counts["failed"], 1)
        self.assertEqual(report.arms["assisted"].outcome_counts["failed"], 1)
        self.assertEqual(report.evaluation_status, "no_metric_population")
        self.assertIsNone(report.arms["direct"].available_output_population.scores.bleu)

    def test_pre_invocation_metadata_failure_and_invalid_provider_output_are_counted(self):
        record = make_annotation()
        metadata_result = run_paired_experiment(record["text"], provider=MetadataFailureProvider())
        metadata_artifact = PairedEvaluationArtifact(schema_version="1.0", example_id=record["id"], result=metadata_result)
        metadata_report = self.evaluate([record], [metadata_artifact])
        self.assertEqual(metadata_report.arms["direct"].pre_invocation_failures, 1)
        self.assertEqual(metadata_report.arms["direct"].attempted_invocations, 0)

        invalid_result = run_paired_experiment(record["text"], provider=InvalidOutputProvider())
        invalid_artifact = PairedEvaluationArtifact(schema_version="1.0", example_id=record["id"], result=invalid_result)
        invalid_report = self.evaluate([record], [invalid_artifact])
        self.assertEqual(invalid_report.arms["direct"].outcome_counts["failed"], 1)
        self.assertEqual(invalid_report.arms["direct"].failure_code_counts["invalid_provider_output"], 1)

    def test_missing_artifact_counts_missing_outputs(self):
        record = make_annotation()
        report = self.evaluate([record], [])
        self.assertEqual(report.arms["direct"].outcome_counts["missing"], 1)
        self.assertEqual(report.arms["assisted"].outcome_counts["missing"], 1)

    def test_matched_aggregate_uses_same_examples_and_difference_sign(self):
        record = make_annotation(text=" nenu   college ")
        artifact = make_artifact(
            record, direct_output="A student went.", assisted_output="I went to college."
        )
        report = self.evaluate([record], [artifact], include_per_example=True)
        self.assertEqual(report.matched_output_pairs, 1)
        self.assertEqual(report.arms["direct"].matched_pair_population.examples, 1)
        self.assertEqual(report.arms["assisted"].matched_pair_population.examples, 1)
        self.assertEqual(report.paired_aggregate_differences.bleu,
                         report.arms["assisted"].matched_pair_population.scores.bleu
                         - report.arms["direct"].matched_pair_population.scores.bleu)
        self.assertEqual(report.per_example_order_counts["bleu"]["higher"], 1)
        self.assertEqual(report.per_example_order_counts["chrf"]["higher"], 1)
        self.assertEqual(report.per_example_comparisons[0].example_id, record["id"])

    def test_multi_example_corpus_metrics_and_differences_use_matched_corpus(self):
        first = make_annotation("one", " nenu   college ", group="g1")
        second = make_annotation("two", " nenu   office ", group="g2")
        artifacts = [
            make_artifact(first, direct_output="I went to college.", assisted_output="I went to college."),
            make_artifact(second, direct_output="I traveled to an office.", assisted_output="I went to college."),
        ]
        report = self.evaluate([first, second], artifacts, include_per_example=True)
        references = [first["reference_translation"], second["reference_translation"]]
        direct = ["I went to college.", "I traveled to an office."]
        assisted = ["I went to college.", "I went to college."]
        self.assertEqual(report.matched_output_pairs, 2)
        self.assertEqual(report.arms["direct"].matched_pair_population.scores.bleu, corpus_bleu(references, direct))
        self.assertEqual(report.arms["assisted"].matched_pair_population.scores.chrf, corpus_chrf(references, assisted))
        self.assertEqual(
            report.paired_aggregate_differences.bleu,
            corpus_bleu(references, assisted) - corpus_bleu(references, direct),
        )
        self.assertEqual(len(report.per_example_comparisons), 2)

    def test_unequal_available_populations_and_per_example_order_counts(self):
        first = make_annotation("one", " nenu   college ", group="g1")
        second = make_annotation("two", " nenu office ", group="g2")
        a = make_artifact(first, error_arms=("assisted",))
        b = make_artifact(second, error_arms=("direct",))
        report = self.evaluate([first, second], [a, b])
        self.assertEqual(report.arms["direct"].available_output_population.examples, 1)
        self.assertEqual(report.arms["assisted"].available_output_population.examples, 1)
        self.assertEqual(report.matched_output_pairs, 0)
        self.assertEqual(report.per_example_order_counts["bleu"]["denominator"], 0)

    def test_arm_identity_survives_execution_order(self):
        record = make_annotation(text=" nenu   college ")
        direct_first = make_artifact(record, direct_output="direct-output", assisted_output="assisted-output")
        assisted_first = make_artifact(record, direct_output="direct-output", assisted_output="assisted-output", order="assisted_first")
        self.assertEqual(direct_first.result.direct.translation.translated_text, "direct-output")
        self.assertEqual(assisted_first.result.direct.translation.translated_text, "direct-output")
        self.assertEqual(assisted_first.result.invocation_order, ["assisted", "direct"])

    def test_contradictory_source_pair_is_invalid_and_excluded_from_metrics(self):
        annotation = make_annotation("id-1", "nenu college")
        different = make_annotation("other", "nenu office")
        artifact = make_artifact(different)
        artifact = artifact.model_copy(update={"example_id": "id-1"})
        report = self.evaluate([annotation], [artifact])
        self.assertEqual(report.arms["direct"].outcome_counts["invalid"], 1)
        self.assertEqual(report.arms["assisted"].outcome_counts["invalid"], 1)
        self.assertEqual(report.arms["direct"].available_output_population.examples, 0)

    def test_incompatible_provider_identity_invalidates_pair_without_mixing_scores(self):
        first = make_annotation("first", " nenu   college ", group="g1")
        second = make_annotation("second", " nenu   office ", group="g2")
        first_artifact = make_artifact(first)
        second_artifact = make_artifact(second)
        updated_result = second_artifact.result.model_copy(update={
            "direct": second_artifact.result.direct.model_copy(update={
                "translation": second_artifact.result.direct.translation.model_copy(update={"provider_id": "different.provider"}),
                "provider_confirmed": second_artifact.result.direct.provider_confirmed.model_copy(update={"provider_id": "different.provider"}),
            }),
            "assisted": second_artifact.result.assisted.model_copy(update={
                "translation": second_artifact.result.assisted.translation.model_copy(update={"provider_id": "different.provider"}),
                "provider_confirmed": second_artifact.result.assisted.provider_confirmed.model_copy(update={"provider_id": "different.provider"}),
            }),
        })
        second_artifact = second_artifact.model_copy(update={"result": updated_result})
        report = self.evaluate([first, second], [first_artifact, second_artifact])
        self.assertEqual(report.invalid_pair_records, 1)
        self.assertEqual(report.arms["direct"].available_output_population.examples, 1)
        self.assertEqual(report.arms["direct"].outcome_counts["invalid"], 1)
        self.assertEqual(report.arms["direct"].failure_code_counts["incompatible_provider_configuration"], 1)
        self.assertEqual(report.arms["direct"].attempted_invocations, 2)

    def test_provider_identifiers_are_safely_filtered(self):
        record = make_annotation()
        artifact = make_artifact(record)
        unsafe = artifact.result.model_copy(update={
            "direct": artifact.result.direct.model_copy(update={
                "translation": artifact.result.direct.translation.model_copy(update={"provider_id": "sk-secret-token"}),
                "provider_confirmed": artifact.result.direct.provider_confirmed.model_copy(update={"provider_id": "sk-secret-token"}),
            }),
            "assisted": artifact.result.assisted.model_copy(update={
                "translation": artifact.result.assisted.translation.model_copy(update={"provider_id": "sk-secret-token"}),
                "provider_confirmed": artifact.result.assisted.provider_confirmed.model_copy(update={"provider_id": "sk-secret-token"}),
            }),
        })
        artifact = artifact.model_copy(update={"result": unsafe})
        report = self.evaluate([record], [artifact])
        self.assertEqual(report.arms["direct"].confirmed_provider_ids, [])

    def test_deterministic_report_and_no_input_mutation(self):
        record = make_annotation()
        original_record = copy.deepcopy(record)
        artifact = make_artifact(record)
        original_artifact = artifact.model_dump(mode="json")
        first = self.evaluate([record], [artifact]).model_dump(mode="json")
        second = self.evaluate([record], [artifact]).model_dump(mode="json")
        self.assertEqual(first, second)
        self.assertEqual(record, original_record)
        self.assertEqual(artifact.model_dump(mode="json"), original_artifact)


class EvaluationCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.annotations = self.root / "annotations.jsonl"
        self.pairs = self.root / "pairs.jsonl"
        self.output = self.root / "report.json"
        self.record = make_annotation()
        self.artifact = make_artifact(self.record)
        self.annotations.write_text(json.dumps(self.record) + "\n", encoding="utf-8")
        self.pairs.write_text(json.dumps(self.artifact.model_dump(mode="json")) + "\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def args(self, output=None, *extra):
        return [
            "--annotations", str(self.annotations),
            "--paired-results", str(self.pairs),
            "--split", "test",
            "--output", str(output or self.output),
            *extra,
        ]

    def test_help_is_available(self):
        stdout = StringIO()
        with redirect_stdout(stdout), self.assertRaises(SystemExit) as caught:
            main(["--help"])
        self.assertEqual(caught.exception.code, 0)
        self.assertIn("--paired-results", stdout.getvalue())

    def test_cli_success_writes_deterministic_machine_report(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            code = main(self.args())
        first = self.output.read_text(encoding="utf-8")
        second_path = self.root / "report-second.json"
        with redirect_stdout(StringIO()):
            second_code = main(self.args(second_path))
        self.assertEqual(code, 0)
        self.assertEqual(second_code, 0)
        self.assertEqual(first, second_path.read_text(encoding="utf-8"))
        self.assertIn('"evaluation_status": "evaluated"', first)
        self.assertEqual(json.loads(first)["per_example_comparisons"], [])
        self.assertNotIn(self.record["text"], first)
        self.assertNotIn(self.record["reference_translation"], first)

    def test_existing_report_is_not_overwritten_without_flag(self):
        self.output.write_text("preserve me", encoding="utf-8")
        stderr = StringIO()
        with redirect_stderr(stderr):
            code = main(self.args())
        self.assertEqual(code, 2)
        self.assertEqual(self.output.read_text(encoding="utf-8"), "preserve me")
        self.assertIn("--overwrite", stderr.getvalue())

    def test_output_cannot_overwrite_inputs_even_with_flag(self):
        original = self.annotations.read_text(encoding="utf-8")
        stderr = StringIO()
        with redirect_stderr(stderr):
            code = main(self.args(self.annotations, "--overwrite"))
        self.assertEqual(code, 2)
        self.assertEqual(self.annotations.read_text(encoding="utf-8"), original)
        self.assertIn("must not overwrite", stderr.getvalue())

    def test_ineligible_dataset_writes_no_score_report_and_exits_nonzero(self):
        draft = make_annotation()
        draft["annotation_status"] = "draft"
        draft["review"] = {"status": "not_reviewed"}
        draft["reference_translation"] = None
        draft["intended_meaning"] = None
        draft["annotation_provenance"]["fields"] = {}
        self.annotations.write_text(json.dumps(draft) + "\n", encoding="utf-8")
        with redirect_stdout(StringIO()):
            code = main(self.args())
        body = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(code, 1)
        self.assertEqual(body["evaluation_status"], "not_evaluated")
        self.assertIsNone(body["arms"]["direct"]["available_output_population"]["scores"]["bleu"])

    def test_no_output_population_exits_nonzero(self):
        self.pairs.write_text("", encoding="utf-8")
        with redirect_stdout(StringIO()):
            code = main(self.args())
        body = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(code, 1)
        self.assertEqual(body["evaluation_status"], "no_metric_population")
        self.assertEqual(body["arms"]["direct"]["outcome_counts"]["missing"], 1)

    def test_malformed_or_missing_inputs_return_actionable_nonzero_without_traceback(self):
        bad_pairs = self.root / "bad-pairs.jsonl"
        bad_pairs.write_text("{bad\n", encoding="utf-8")
        stderr = StringIO()
        with redirect_stderr(stderr):
            code = main([
                "--annotations", str(self.annotations), "--paired-results", str(bad_pairs),
                "--split", "test", "--output", str(self.output),
            ])
        self.assertEqual(code, 2)
        self.assertIn("line 1: malformed JSON", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())
        missing = StringIO()
        with redirect_stderr(missing):
            missing_code = main([
                "--annotations", str(self.root / "missing.jsonl"), "--paired-results", str(self.pairs),
                "--split", "test", "--output", str(self.output),
            ])
        self.assertEqual(missing_code, 2)
        self.assertIn("structural validation failed", missing.getvalue())
        bad_annotations = self.root / "bad-annotations.jsonl"
        bad_annotations.write_text("{bad\n", encoding="utf-8")
        malformed = StringIO()
        with redirect_stderr(malformed):
            malformed_code = main([
                "--annotations", str(bad_annotations), "--paired-results", str(self.pairs),
                "--split", "test", "--output", str(self.output),
            ])
        self.assertEqual(malformed_code, 2)
        self.assertIn("malformed JSON", malformed.getvalue())

    def test_invalid_paired_schema_is_rejected_without_exposing_values(self):
        self.pairs.write_text('{"schema_version":"1.0","example_id":"x","result":{}}\n', encoding="utf-8")
        stderr = StringIO()
        with redirect_stderr(stderr):
            code = main(self.args())
        self.assertEqual(code, 2)
        self.assertIn("schema error", stderr.getvalue())
        self.assertNotIn("synthetic secret-bearing", stderr.getvalue())

    def test_unknown_nested_paired_fields_are_rejected(self):
        artifact = json.loads(self.pairs.read_text(encoding="utf-8"))
        artifact["result"]["assisted"]["unexpected_secret"] = "do not print"
        self.pairs.write_text(json.dumps(artifact) + "\n", encoding="utf-8")
        stderr = StringIO()
        with redirect_stderr(stderr):
            code = main(self.args())
        self.assertEqual(code, 2)
        self.assertIn("unsupported property", stderr.getvalue())
        self.assertNotIn("do not print", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
