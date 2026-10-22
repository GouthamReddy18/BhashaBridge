import json
import tempfile
import unittest
from pathlib import Path

from app.services.experiment_execution import ExperimentExecutionError, run_dataset_experiment
from app.services.preprocessing import normalize_whitespace
from app.services.tokenization import tokenize
from app.services.translation import ProviderTranslation


def reviewed_test_fixture():
    """Synthetic test-only row; it is not real reviewed evaluation data."""
    text = "  nenu\tcollege  "
    normalized = normalize_whitespace(text)
    return {
        "annotation_version": "1.0", "id": "test-only-01", "text": text,
        "normalized_text": normalized, "source_type": "synthetic_unit_test",
        "annotation_status": "reviewed",
        "annotation_provenance": {
            "method": "synthetic_test_fixture", "details": "No real reviewer or source.", "origin": "human",
            "fields": {name: {"origin": "human", "review_status": "reviewed",
                "details": "Synthetic test placeholder.", "source_reference": "fixture:test"}
                for name in ("reference_translation", "intended_meaning")},
        },
        "tokens": [{"index": token.index, "surface": token.text, "start": token.start,
            "end": token.end, "language_label": "TELUGU_ROMANIZED" if token.text == "nenu" else "ENGLISH"}
            for token in tokenize(normalized)],
        "reference_translation": "I went to college.",
        "intended_meaning": "Synthetic intended meaning for software tests.",
        "review": {"status": "reviewed", "reviewer_id": "test-only", "reviewed_at": "2026-01-10"},
        "split": "test", "split_group": "synthetic-test-group",
    }


class SyntheticProvider:
    provider_id = "mock.test"

    def __init__(self):
        self.calls = []

    def translate(self, request):
        self.calls.append(request.text)
        return ProviderTranslation("Synthetic test output; not a translation.")


class OneFailureProvider(SyntheticProvider):
    def translate(self, request):
        self.calls.append(request.text)
        if request.text.startswith("  nenu"):
            raise RuntimeError("synthetic provider failure")
        return ProviderTranslation("Synthetic test output; not a translation.")


class ExperimentExecutionTests(unittest.TestCase):
    def write_dataset(self, path, row=None):
        path.write_text(json.dumps(row or reviewed_test_fixture(), ensure_ascii=False) + "\n", encoding="utf-8")

    def test_ready_dataset_writes_versioned_ids_split_and_actual_order(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, output = Path(directory) / "annotations.jsonl", Path(directory) / "paired.jsonl"
            self.write_dataset(dataset)
            provider = SyntheticProvider()
            result = run_dataset_experiment(dataset, output, split="test", provider=provider,
                allow_provider_calls=True)
            artifact = json.loads(result.read_text(encoding="utf-8"))
            self.assertEqual(artifact["schema_version"], "1.0")
            self.assertEqual(artifact["example_id"], "test-only-01")
            self.assertEqual(artifact["split"], "test")
            self.assertEqual(artifact["result"]["direct"]["intended_input"], "  nenu\tcollege  ")
            self.assertEqual(artifact["result"]["invocation_order"], ["direct", "assisted"])
            self.assertEqual(provider.calls[0], "  nenu\tcollege  ")
            self.assertEqual(len(provider.calls), 2)

    def test_nonready_dataset_and_missing_opt_in_do_not_call_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, output = Path(directory) / "annotations.jsonl", Path(directory) / "paired.jsonl"
            row = reviewed_test_fixture()
            row["annotation_status"] = "draft"
            row["review"] = {"status": "not_reviewed"}
            self.write_dataset(dataset, row)
            provider = SyntheticProvider()
            with self.assertRaises(ExperimentExecutionError):
                run_dataset_experiment(dataset, output, split="test", provider=provider,
                    allow_provider_calls=True)
            self.assertEqual(provider.calls, [])
            self.write_dataset(dataset)
            with self.assertRaisesRegex(ExperimentExecutionError, "explicit"):
                run_dataset_experiment(dataset, output, split="test", provider=provider)
            self.assertEqual(provider.calls, [])

    def test_existing_output_is_never_overwritten_or_invoked(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, output = Path(directory) / "annotations.jsonl", Path(directory) / "paired.jsonl"
            self.write_dataset(dataset)
            output.write_text("preserve", encoding="utf-8")
            provider = SyntheticProvider()
            with self.assertRaisesRegex(ExperimentExecutionError, "already exists"):
                run_dataset_experiment(dataset, output, split="test", provider=provider,
                    allow_provider_calls=True)
            self.assertEqual(provider.calls, [])
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve")

    def test_failed_arm_is_recorded_without_retrying(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, output = Path(directory) / "annotations.jsonl", Path(directory) / "paired.jsonl"
            self.write_dataset(dataset)
            provider = OneFailureProvider()
            run_dataset_experiment(dataset, output, split="test", provider=provider,
                allow_provider_calls=True)
            artifact = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(artifact["result"]["direct"]["translation"]["status"], "failed")
            self.assertEqual(artifact["result"]["assisted"]["translation"]["status"], "success")
            self.assertEqual(provider.calls, ["  nenu\tcollege  ", "nenu college"])


if __name__ == "__main__":
    unittest.main()
