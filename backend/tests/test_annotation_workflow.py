import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from app.services.annotation_workflow import (
    WorkflowError,
    create_draft,
    export_ready_dataset,
    write_revision_manifest,
)
from app.services.preprocessing import normalize_whitespace
from app.services.tokenization import tokenize
from app.services.dataset_validation import validate_dataset


def eligible_test_record():
    """Synthetic software fixture only; never evidence of a human review."""
    text = "nenu college"
    normalized = normalize_whitespace(text)
    return {
        "annotation_version": "1.0",
        "id": "test-only-001",
        "text": text,
        "normalized_text": normalized,
        "source_type": "synthetic_unit_test",
        "annotation_status": "reviewed",
        "annotation_provenance": {
            "method": "synthetic_fixture",
            "details": "Synthetic software test data; no real reviewer or source.",
            "origin": "human",
            "fields": {
                field: {
                    "origin": "human",
                    "review_status": "reviewed",
                    "details": "Synthetic test placeholder only.",
                    "source_reference": "synthetic-test-only",
                }
                for field in ("reference_translation", "intended_meaning")
            },
        },
        "tokens": [
            {"index": token.index, "surface": token.text, "start": token.start, "end": token.end,
             "language_label": "TELUGU_ROMANIZED" if token.text == "nenu" else "ENGLISH"}
            for token in tokenize(normalized)
        ],
        "reference_translation": "I went to college.",
        "intended_meaning": "The speaker went to college.",
        "review": {"status": "reviewed", "reviewer_id": "test-only", "reviewed_at": "2026-01-10"},
        "split": "test",
        "split_group": "synthetic-group",
    }


class AnnotationWorkflowTests(unittest.TestCase):
    def test_create_draft_is_unicode_correct_and_never_claims_review(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "draft.jsonl"
            create_draft(path, record_id="draft-1", text="  nenu\tహలో! 42 🙂 ",
                         source_type="user_supplied_draft", source_details="Source details supplied by annotator.")
            report = validate_dataset(path)
            record = json.loads(path.read_text(encoding="utf-8"))

        self.assertTrue(report.valid, report.errors)
        self.assertEqual(record["annotation_status"], "draft")
        self.assertEqual(record["review"], {"status": "not_reviewed"})
        self.assertEqual(record["annotation_provenance"]["origin"], "machine")
        self.assertIsNone(record["reference_translation"])
        self.assertIsNone(record["intended_meaning"])
        self.assertEqual(record["normalized_text"], "nenu హలో! 42 🙂")
        self.assertEqual(record["tokens"][-2]["language_label"], "NUMBER")
        self.assertEqual(record["tokens"][-1]["language_label"], "PUNCTUATION")

    def test_create_draft_refuses_existing_destination_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "draft.jsonl"
            path.write_bytes(b"keep me")
            with self.assertRaisesRegex(WorkflowError, "already exists"):
                create_draft(path, record_id="x", text="nenu", source_type="draft", source_details="fixture")
            self.assertEqual(path.read_bytes(), b"keep me")

    def test_export_requires_ready_dataset_and_does_not_create_failure_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "drafts.jsonl"
            output = Path(directory) / "export.jsonl"
            source.write_text(json.dumps({"annotation_version": "1.0"}) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(WorkflowError, "not evaluation-ready"):
                export_ready_dataset(source, output)
            self.assertFalse(output.exists())

    def test_export_copies_eligible_input_exactly_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "eligible.jsonl"
            output = Path(directory) / "export.jsonl"
            payload = (json.dumps(eligible_test_record(), ensure_ascii=False) + "\n").encode("utf-8")
            source.write_bytes(payload)
            export_ready_dataset(source, output)
            self.assertEqual(output.read_bytes(), payload)
            with self.assertRaisesRegex(WorkflowError, "already exists"):
                export_ready_dataset(source, output)
            self.assertEqual(output.read_bytes(), payload)
            with self.assertRaisesRegex(WorkflowError, "must differ"):
                export_ready_dataset(source, source)

    def test_revision_manifest_is_hash_linked_and_lists_exact_changed_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original, revised = root / "old.jsonl", root / "new.jsonl"
            manifest = root / "revision.json"
            old = eligible_test_record()
            new = dict(old, annotation_notes="Corrected punctuation after review.")
            original.write_text(json.dumps(old, ensure_ascii=False) + "\n", encoding="utf-8")
            revised.write_text(json.dumps(new, ensure_ascii=False) + "\n", encoding="utf-8")
            old_digest = hashlib.sha256(original.read_bytes()).hexdigest()
            new_digest = hashlib.sha256(revised.read_bytes()).hexdigest()
            write_revision_manifest(original, revised, manifest, change_note="Human-authored revision note")
            data = json.loads(manifest.read_text(encoding="utf-8"))

        self.assertEqual(data["changed_record_ids"], ["test-only-001"])
        self.assertEqual(data["source_sha256"], old_digest)
        self.assertEqual(data["revised_sha256"], new_digest)
        self.assertEqual(len(data["revision_id"]), 64)

    def test_revision_manifest_rejects_id_changes_and_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original, revised, manifest = root / "old.jsonl", root / "new.jsonl", root / "rev.json"
            original.write_text(json.dumps(eligible_test_record()) + "\n", encoding="utf-8")
            record = eligible_test_record()
            record["id"] = "different-id"
            revised.write_text(json.dumps(record) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(WorkflowError, "preserve the set"):
                write_revision_manifest(original, revised, manifest, change_note="test")
            self.assertFalse(manifest.exists())
            manifest.write_text("preserve", encoding="utf-8")
            changed = eligible_test_record()
            changed["annotation_notes"] = "changed"
            revised.write_text(json.dumps(changed) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(WorkflowError, "already exists"):
                write_revision_manifest(original, revised, manifest, change_note="test")
            self.assertEqual(manifest.read_text(encoding="utf-8"), "preserve")


if __name__ == "__main__":
    unittest.main()
