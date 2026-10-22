import json
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from app.schemas.evaluation import PairedEvaluationArtifact
from app.schemas.human_rating import HumanRatingRecord
from app.services.experiment import run_paired_experiment
from app.services.human_rating_workflow import (
    RUBRIC_VERSION, RatingWorkflowError, aggregate_human_ratings, create_rating_tasks,
)
from app.services.preprocessing import normalize_whitespace
from app.services.tokenization import tokenize
from app.services.translation import ProviderTranslation


def reviewed_fixture():
    text = "  nenu\tcollege  "
    normalized = normalize_whitespace(text)
    return {
        "annotation_version": "1.0", "id": "rating-test-1", "text": text,
        "normalized_text": normalized, "source_type": "synthetic_unit_test",
        "annotation_status": "reviewed",
        "annotation_provenance": {
            "method": "synthetic test", "details": "No actual human review.", "origin": "human",
            "fields": {name: {"origin": "human", "review_status": "reviewed",
                "details": "Test only.", "source_reference": "fixture:test"}
                for name in ("reference_translation", "intended_meaning")},
        },
        "tokens": [{"index": t.index, "surface": t.text, "start": t.start, "end": t.end,
                    "language_label": "TELUGU_ROMANIZED" if t.text == "nenu" else "ENGLISH"}
                   for t in tokenize(normalized)],
        "reference_translation": "I went to college.",
        "intended_meaning": "Test-only intended meaning.",
        "review": {"status": "reviewed", "reviewer_id": "test-only", "reviewed_at": "2026-01-10"},
        "split": "test", "split_group": "rating-test-group",
    }


class Provider:
    provider_id = "google.cloud.translation.basic.v2"
    def translate(self, request):
        return ProviderTranslation("Synthetic output; test only.")


def record(example_id, arm=None, label=None, rating=None, status="pending", reviewer=None):
    return {
        "schema_version": "1.0", "rubric_version": RUBRIC_VERSION,
        "example_id": example_id, "arm": arm, "display_label": label,
        "rating": rating, "status": status, "reviewer_id": reviewer,
        "reviewer_provenance": "test-only reviewer declaration" if reviewer else None,
        "reviewed_at": "2026-01-10" if reviewer else None,
    }


class HumanRatingWorkflowTests(unittest.TestCase):
    def test_rating_schema_rejects_out_of_range_bool_and_incomplete_completion(self):
        for values in (
            record("x", arm="direct", rating=5, status="complete", reviewer="r"),
            record("x", arm="direct", rating=True, status="complete", reviewer="r"),
            record("x", arm="direct", rating=3, status="complete"),
        ):
            with self.assertRaises(ValidationError):
                HumanRatingRecord.model_validate(values)

    def test_unblinded_tasks_are_pending_and_never_invent_scores(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            annotations, pairs = root / "data.jsonl", root / "pairs.jsonl"
            row = reviewed_fixture()
            annotations.write_text(json.dumps(row) + "\n", encoding="utf-8")
            result = run_paired_experiment(row["text"], provider=Provider())
            paired = PairedEvaluationArtifact(schema_version="1.0", example_id=row["id"], split="test", result=result)
            pairs.write_text(paired.model_dump_json() + "\n", encoding="utf-8")
            tasks, ratings = root / "tasks.jsonl", root / "ratings.jsonl"
            create_rating_tasks(annotations, pairs, split="test", tasks_output=tasks,
                                ratings_output=ratings)
            task = json.loads(tasks.read_text(encoding="utf-8"))
            rows = [json.loads(line) for line in ratings.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(task["source_text"], row["text"])
            self.assertEqual(task["intended_meaning"], row["intended_meaning"])
            self.assertEqual({item["display_label"] for item in task["items"]}, {"direct", "assisted"})
            self.assertTrue(all(item["status"] == "pending" and item["rating"] is None for item in rows))
            report = aggregate_human_ratings(tasks, ratings)
            self.assertEqual(report["arms"]["direct"]["rating_distribution"],
                             {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0})
            self.assertEqual(report["arms"]["direct"]["missing_or_insufficiently_reviewed_examples"], 1)
            self.assertEqual(report["inter_annotator_agreement"]["status"], "not_calculated")

    def test_unregistered_provider_cannot_enter_rating_tasks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = reviewed_fixture()
            annotations, pairs = root / "data.jsonl", root / "pairs.jsonl"
            annotations.write_text(json.dumps(row) + "\n", encoding="utf-8")
            result = run_paired_experiment(row["text"], provider=Provider())
            for arm in ("direct", "assisted"):
                arm_result = getattr(result, arm)
                arm_result.translation = arm_result.translation.model_copy(update={"provider_id": "fixture.fake"})
                arm_result.provider_confirmed = arm_result.provider_confirmed.model_copy(update={"provider_id": "fixture.fake"})
            paired = PairedEvaluationArtifact(schema_version="1.0", example_id=row["id"], split="test", result=result)
            pairs.write_text(paired.model_dump_json() + "\n", encoding="utf-8")
            with self.assertRaisesRegex(RatingWorkflowError, "unregistered provider"):
                create_rating_tasks(
                    annotations, pairs, split="test", tasks_output=root / "tasks.jsonl",
                    ratings_output=root / "ratings.jsonl",
                )

    def test_blinded_tasks_separate_mapping_and_aggregate_by_actual_arm(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tasks = root / "tasks.jsonl"
            tasks.write_text(json.dumps({"schema_version": "1.0", "rubric_version": RUBRIC_VERSION,
                "example_id": "e1", "blinded": True, "items": [
                    {"display_label": "A", "translation_text": "text A"},
                    {"display_label": "B", "translation_text": "text B"},
                ]}) + "\n", encoding="utf-8")
            mapping = root / "mapping.json"
            mapping.write_text(json.dumps({"schema_version": "1.0", "mapping": [
                {"example_id": "e1", "display_label": "A", "arm": "assisted"},
                {"example_id": "e1", "display_label": "B", "arm": "direct"},
            ]}), encoding="utf-8")
            ratings = root / "ratings.jsonl"
            ratings.write_text("\n".join(json.dumps(record("e1", label=label, rating=score,
                status="complete", reviewer="reviewer-1")) for label, score in (("A", 4), ("B", 2))) + "\n",
                encoding="utf-8")
            report = aggregate_human_ratings(tasks, ratings, mapping_path=mapping)
            self.assertEqual(report["arms"]["assisted"]["rating_distribution"]["4"], 1)
            self.assertEqual(report["arms"]["direct"]["rating_distribution"]["2"], 1)
            self.assertTrue(report["blinded_presentation"])

    def test_missing_blind_key_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tasks, ratings = root / "tasks.jsonl", root / "ratings.jsonl"
            tasks.write_text(json.dumps({"schema_version": "1.0", "rubric_version": RUBRIC_VERSION,
                "example_id": "e1", "blinded": True, "items": [
                    {"display_label": "A", "translation_text": "a"},
                    {"display_label": "B", "translation_text": "b"},
                ]}) + "\n", encoding="utf-8")
            ratings.write_text(json.dumps(record("e1", label="A", rating=4, status="complete", reviewer="r")) + "\n",
                               encoding="utf-8")
            with self.assertRaisesRegex(RatingWorkflowError, "mapping"):
                aggregate_human_ratings(tasks, ratings)

    def test_missing_translation_is_reported_outside_rating_denominator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tasks, ratings = root / "tasks.jsonl", root / "ratings.jsonl"
            tasks.write_text(json.dumps({"schema_version": "1.0", "rubric_version": RUBRIC_VERSION,
                "example_id": "e1", "blinded": False, "items": [
                    {"display_label": "direct", "translation_text": None},
                    {"display_label": "assisted", "translation_text": "output"},
                ]}) + "\n", encoding="utf-8")
            ratings.write_text(json.dumps(record("e1", arm="direct")) + "\n" +
                               json.dumps(record("e1", arm="assisted")) + "\n", encoding="utf-8")
            report = aggregate_human_ratings(tasks, ratings)
            self.assertEqual(report["arms"]["direct"]["unavailable_output_examples"], 1)
            self.assertEqual(report["arms"]["direct"]["pending_judgments"], 0)
            self.assertEqual(report["arms"]["direct"]["available_output_examples"], 0)

    def test_duplicate_reviewer_and_insufficient_independent_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tasks, ratings = root / "tasks.jsonl", root / "ratings.jsonl"
            tasks.write_text(json.dumps({"schema_version": "1.0", "rubric_version": RUBRIC_VERSION,
                "example_id": "e1", "blinded": False, "items": [
                    {"display_label": "direct", "translation_text": "a"},
                    {"display_label": "assisted", "translation_text": "b"},
                ]}) + "\n", encoding="utf-8")
            judgments = [record("e1", arm="direct", rating=3, status="complete", reviewer="r1"),
                         record("e1", arm="direct", rating=4, status="complete", reviewer="r1")]
            ratings.write_text("".join(json.dumps(row) + "\n" for row in judgments), encoding="utf-8")
            with self.assertRaisesRegex(RatingWorkflowError, "duplicate"):
                aggregate_human_ratings(tasks, ratings, min_reviewers=2)
            ratings.write_text(json.dumps(judgments[0]) + "\n", encoding="utf-8")
            report = aggregate_human_ratings(tasks, ratings, min_reviewers=2)
            self.assertEqual(report["arms"]["direct"]["rated_examples_with_required_reviewers"], 0)
            self.assertEqual(report["arms"]["direct"]["missing_or_insufficiently_reviewed_examples"], 1)


if __name__ == "__main__":
    unittest.main()
