import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from pydantic import ValidationError

from app.schemas.analysis import TranslationResult
from app.schemas.four_condition import FourConditionArtifact, FourConditionConfiguration
from app.schemas.four_condition import ConditionResourceBinding
from app.schemas.linguistic_resource import LinguisticResourceManifest
from app.services.four_condition_experiment import _apply_mapping_rules, run_four_condition_experiment
from app.services.four_condition_evaluation import (
    evaluate_four_condition_records, validate_four_condition_report,
)
from app.services.evaluation_readiness import EvaluationReadinessReport
from backend.tests.test_evaluation import make_annotation
from scripts.evaluate_four_condition_experiment import main as evaluate_cli
from scripts.validate_four_condition_report import main as validate_cli


class FakeProvider:
    provider_id = "fixture.fake"

    def __init__(self):
        self.inputs = []

    def translate(self, request):
        self.inputs.append(request.text)
        from app.services.translation import ProviderTranslation
        return ProviderTranslation("synthetic output")


class FourConditionTests(unittest.TestCase):
    @staticmethod
    def normalizer_binding():
        manifest = LinguisticResourceManifest.model_validate({
            "schema_version": "1.0", "resource_id": "synthetic-normalizer",
            "resource_version": "1", "provenance": "Synthetic test fixture only.",
            "language_coverage": ["ENGLISH", "TELUGU_ROMANIZED"],
            "rules": [{
                "rule_id": "test.normalizer.nenu", "rule_version": "1",
                "source_surface": "nenu", "source_language": "TELUGU_ROMANIZED",
                "replacement": "nēnu", "replacement_language": "TELUGU_ROMANIZED",
                "applicability": "exact_surface_and_language_match",
                "provenance": "Synthetic test fixture only.",
                "evidence_references": ["fixture:test"], "review_status": "reviewed",
                "reviewer_id": "test", "reviewed_at": "2026-01-01",
                "entity_preservation": "confirmed_non_entity",
            }],
        })
        return ConditionResourceBinding(kind="normalizer", manifest=manifest, test_only=True)

    def test_missing_resources_block_incremental_conditions_and_preserve_direct_input(self):
        provider = FakeProvider()
        config = FourConditionConfiguration(dataset_label="test-fixture", split="test")
        artifact = run_four_condition_experiment(
            "fixture-001", "  nenu   bank account  ", configuration=config,
            provider=provider, allow_provider_calls=True, allow_test_fixtures=True,
        )
        self.assertEqual(provider.inputs, ["  nenu   bank account  "])
        self.assertEqual(artifact.result.conditions[0].intended_provider_input, "  nenu   bank account  ")
        self.assertEqual([c.status for c in artifact.result.conditions], ["completed", "blocked", "blocked", "blocked"])
        self.assertEqual(artifact.result.conditions[1].blocked_reason, "resource_missing:normalizer")
        self.assertEqual(artifact.result.conditions[2].blocked_reason, "dependency_blocked:normalized_v1")
        self.assertTrue(artifact.result.test_fixture)
        self.assertFalse(any(c.research_eligible for c in artifact.result.conditions))

    def test_unknown_provider_output_stays_tainted_after_json_round_trip(self):
        config = FourConditionConfiguration(dataset_label="synthetic-test-only", split="test")
        artifact = run_four_condition_experiment(
            "fixture-001", "nenu college", configuration=config,
            provider=FakeProvider(), allow_provider_calls=True,
        )
        restored = FourConditionArtifact.model_validate(artifact.model_dump(mode="json"))
        self.assertTrue(restored.result.test_fixture)
        self.assertFalse(any(item.research_eligible for item in restored.result.conditions))

    def test_test_only_resource_transformation_is_consistent_and_tainted(self):
        config = FourConditionConfiguration(
            dataset_label="synthetic-test-only", split="test",
            resources={"normalizer": self.normalizer_binding()},
        )
        artifact = run_four_condition_experiment(
            "fixture-001", "nenu college", configuration=config,
            provider=None, allow_test_fixtures=True,
        )
        restored = FourConditionArtifact.model_validate(artifact.model_dump(mode="json"))
        normalized = restored.result.conditions[1]
        self.assertEqual(normalized.intended_provider_input, "nēnu college")
        self.assertEqual(normalized.stages[0].applied_transformations, 1)
        self.assertTrue(restored.result.test_fixture)
        self.assertFalse(any(item.research_eligible for item in restored.result.conditions))

    def test_configuration_rejects_duplicate_or_incomplete_condition_order(self):
        with self.assertRaises(ValidationError):
            FourConditionConfiguration(
                dataset_label="test", split="test",
                execution_order=("direct_v1", "direct_v1", "transliterated_v1", "ambiguity_aware_v1"),
            )

    def test_mapping_preserves_whitespace_and_uses_source_codepoint_offsets(self):
        source = "😀   nenu, bank"
        output, changes, _, _ = _apply_mapping_rules(source, self.normalizer_binding())
        self.assertEqual(output, "😀   nēnu, bank")
        self.assertEqual(len(changes), 1)
        self.assertEqual(source[changes[0].start:changes[0].end], "nenu")
        self.assertEqual(changes[0].after, "nēnu")

    def test_resource_taint_metadata_is_required_not_defaulted(self):
        raw = self.normalizer_binding().model_dump(mode="python")
        raw.pop("test_only")
        with self.assertRaises(ValidationError):
            ConditionResourceBinding.model_validate(raw)

    def test_artifact_rejects_completed_variant_without_its_resources(self):
        annotation = make_annotation()
        config = FourConditionConfiguration(dataset_label="audit-test", split="test")
        raw = run_four_condition_experiment(
            annotation["id"], annotation["text"], configuration=config, provider=None,
        ).model_dump(mode="python")
        normalized = raw["result"]["conditions"][1]
        normalized.update(
            status="completed", blocked_reason=None,
            intermediate_inputs={"original": annotation["text"]},
            intended_provider_input=annotation["text"], provider_input=annotation["text"],
            provider_call_attempted=True,
            translation={
                "status": "success", "input_text": annotation["text"],
                "provider_id": "fixture.fake", "translated_text": "synthetic output",
                "provider_model": None, "provider_configuration_forwarded": False,
            },
            resource_references=(), transformations=(), skipped_transformations=(),
            stages=(), intervention_applied=False, research_eligible=True,
        )
        raw["result"]["invocation_order"] = ["normalized_v1"]
        with self.assertRaises(ValidationError):
            FourConditionArtifact.model_validate(raw)

    def test_research_ineligible_outputs_are_never_scored(self):
        annotation = make_annotation()
        config = FourConditionConfiguration(dataset_label="audit-test", split="test")
        artifact = run_four_condition_experiment(
            annotation["id"], annotation["text"], configuration=config,
            provider=FakeProvider(), allow_provider_calls=True,
        )
        conditions = list(artifact.result.conditions)
        direct = conditions[0]
        conditions[0] = direct.model_copy(update={
            "research_eligible": False,
            "translation": direct.translation.model_copy(update={
                "provider_id": "google.cloud.translation.basic.v2",
            }),
        })
        forged = artifact.model_copy(update={
            "result": artifact.result.model_copy(update={
                "test_fixture": False, "conditions": tuple(conditions),
            }),
        })
        report = evaluate_four_condition_records(
            dataset_label="audit-test", split="test", annotation_rows=[(1, annotation)],
            readiness=EvaluationReadinessReport(path="fixture", records_examined=1),
            artifacts=[forged],
        )
        self.assertEqual(report.report_status, "test_fixture_only")
        self.assertEqual(report.variants["direct_v1"].available_examples, 0)

    def test_incompatible_provider_configuration_forwarding_is_excluded(self):
        annotations = [make_annotation("one"), make_annotation("two")]
        config = FourConditionConfiguration(dataset_label="audit-test", split="test")
        artifacts = []
        for index, annotation in enumerate(annotations):
            artifact = run_four_condition_experiment(
                annotation["id"], annotation["text"], configuration=config, provider=None,
            )
            conditions = list(artifact.result.conditions)
            direct = conditions[0]
            conditions[0] = direct.model_copy(update={
                "provider_call_attempted": True,
                "provider_input": annotation["text"],
                "translation": TranslationResult(
                    status="success", input_text=annotation["text"],
                    provider_id="google.cloud.translation.basic.v2",
                    translated_text="synthetic test output",
                    provider_configuration_forwarded=True if index else None,
                ),
            })
            result = artifact.result.model_copy(update={
                "conditions": tuple(conditions), "invocation_order": ("direct_v1",),
            })
            artifacts.append(artifact.model_copy(update={"result": result}))
        report = evaluate_four_condition_records(
            dataset_label="audit-test", split="test",
            annotation_rows=[(index + 1, row) for index, row in enumerate(annotations)],
            readiness=EvaluationReadinessReport(path="fixture", records_examined=2),
            artifacts=artifacts,
        )
        self.assertEqual(report.variants["direct_v1"].available_examples, 1)
        self.assertEqual(report.variants["direct_v1"].outcome_counts["invalid_pair"], 1)

    def test_test_fixture_outcomes_are_never_scored_as_research(self):
        annotation = make_annotation()
        config = FourConditionConfiguration(dataset_label="test-fixture", split="test")
        artifact = run_four_condition_experiment(
            annotation["id"], annotation["text"], configuration=config,
            provider=FakeProvider(), allow_provider_calls=True, allow_test_fixtures=True,
        )
        readiness = EvaluationReadinessReport(path="fixture", records_examined=1)
        report = evaluate_four_condition_records(
            dataset_label="test-fixture", split="test", annotation_rows=[(1, annotation)],
            readiness=readiness, artifacts=[artifact],
        )
        self.assertEqual(report.report_status, "test_fixture_only")
        self.assertEqual(report.variants["direct_v1"].available_examples, 0)
        self.assertEqual(report.variants["direct_v1"].outcome_counts["test_fixture_only"], 1)
        valid, errors = validate_four_condition_report(report.model_dump(mode="json"))
        self.assertTrue(valid, errors)

    def test_report_validator_rejects_inconsistent_comparison_references(self):
        annotation = make_annotation()
        config = FourConditionConfiguration(dataset_label="test-fixture", split="test")
        artifact = run_four_condition_experiment(
            annotation["id"], annotation["text"], configuration=config,
            provider=None, allow_test_fixtures=True,
        )
        readiness = EvaluationReadinessReport(path="fixture", records_examined=1)
        report = evaluate_four_condition_records(
            dataset_label="test-fixture", split="test", annotation_rows=[(1, annotation)],
            readiness=readiness, artifacts=[artifact],
        ).model_dump(mode="json")
        report["comparisons"][0]["numerator_condition"] = "ambiguity_aware_v1"
        valid, errors = validate_four_condition_report(report)
        self.assertFalse(valid)
        self.assertTrue(any("condition references" in error for error in errors))

    def test_synthetic_labeled_jsonl_runs_through_evaluator_and_report_cli(self):
        annotation = make_annotation()
        config = FourConditionConfiguration(dataset_label="synthetic-test-only", split="test")
        artifact = run_four_condition_experiment(
            annotation["id"], annotation["text"], configuration=config,
            provider=None, allow_test_fixtures=True,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            annotations = root / "annotations.jsonl"
            artifacts = root / "artifacts.jsonl"
            report = root / "report.json"
            annotations.write_text(json.dumps(annotation) + "\n", encoding="utf-8")
            artifacts.write_text(json.dumps(artifact.model_dump(mode="json")) + "\n", encoding="utf-8")
            with redirect_stdout(StringIO()):
                status = evaluate_cli([
                    "--annotations", str(annotations), "--artifacts", str(artifacts),
                    "--dataset-label", "synthetic-test-only", "--split", "test",
                    "--output", str(report),
                ])
                validation = validate_cli([str(report)])
            self.assertEqual(status, 1)  # Fixture or readiness-blocked; never research-ready.
            self.assertEqual(validation, 0)


if __name__ == "__main__":
    unittest.main()
