import json
import tempfile
import unittest
from pathlib import Path

from app.schemas.linguistic_resource import LinguisticResourceManifest
from app.services.linguistic_resources import ResourceError, load_resource, match_rule, resource_readiness


def resource(*, status="reviewed", entity="confirmed_non_entity"):
    return LinguisticResourceManifest.model_validate({
        "schema_version": "1.0", "resource_id": "test-only", "resource_version": "1",
        "provenance": "Synthetic unit-test fixture; not linguistic evidence.",
        "language_coverage": ["ENGLISH", "TELUGU_ROMANIZED"],
        "rules": [{
            "rule_id": "test.exact", "rule_version": "1", "source_surface": "foo",
            "source_language": "TELUGU_ROMANIZED", "replacement": "bar",
            "replacement_language": "ENGLISH", "applicability": "synthetic test only",
            "provenance": "synthetic unit-test fixture", "evidence_references": ["fixture:test"],
            "review_status": status,
            "reviewer_id": "test-reviewer" if status == "reviewed" else None,
            "reviewed_at": "2026-01-01" if status == "reviewed" else None,
            "entity_preservation": entity,
        }],
    })


class LinguisticResourceTests(unittest.TestCase):
    def test_exact_matching_is_deterministic_and_casefolded(self):
        manifest = resource()
        first = match_rule(manifest, token_surface="FOO", token_language="TELUGU_ROMANIZED", applicable=True, entity_preserved=True)
        second = match_rule(manifest, token_surface="FOO", token_language="TELUGU_ROMANIZED", applicable=True, entity_preserved=True)
        self.assertEqual(first, second)
        self.assertEqual(first.rule_id, "test.exact")

    def test_match_abstains_for_inapplicable_entity_uncertain_or_unreviewed(self):
        reviewed = resource()
        self.assertIsNone(match_rule(reviewed, token_surface="foo", token_language="TELUGU_ROMANIZED", applicable=False, entity_preserved=True))
        self.assertIsNone(match_rule(reviewed, token_surface="foo", token_language="TELUGU_ROMANIZED", applicable=True, entity_preserved=False))
        self.assertIsNone(match_rule(resource(status="pending"), token_surface="foo", token_language="TELUGU_ROMANIZED", applicable=True, entity_preserved=True))
        self.assertIsNone(match_rule(reviewed, token_surface="foo", token_language="UNKNOWN", applicable=True, entity_preserved=True))

    def test_empty_resource_is_blocked(self):
        manifest = LinguisticResourceManifest.model_validate({
            "schema_version": "1.0", "resource_id": "empty", "resource_version": "1",
            "provenance": "No verified resource supplied.", "language_coverage": ["ENGLISH"], "rules": [],
        })
        self.assertEqual(resource_readiness(manifest), ("resource:no_rules_available",))

    def test_rejected_resource_and_non_boolean_conditions_fail_closed(self):
        rejected = resource(status="rejected")
        self.assertIn("test.exact:review_rejected", resource_readiness(rejected))
        self.assertIsNone(match_rule(resource(), token_surface="foo", token_language="TELUGU_ROMANIZED", applicable="yes", entity_preserved=True))

    def test_rejects_inconsistent_review_metadata_and_duplicate_ids(self):
        raw = resource().model_dump(mode="json")
        raw["rules"][0]["reviewer_id"] = None
        with self.assertRaises(ValueError):
            LinguisticResourceManifest.model_validate(raw)
        raw = resource().model_dump(mode="json")
        raw["rules"].append(raw["rules"][0])
        with self.assertRaises(ValueError):
            LinguisticResourceManifest.model_validate(raw)

    def test_loader_rejects_duplicate_json_keys_and_sanitizes_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resource.json"
            path.write_text('{"schema_version":"1.0","schema_version":"1.0"}', encoding="utf-8")
            with self.assertRaisesRegex(ResourceError, "invalid linguistic resource"):
                load_resource(path)

    def test_loader_accepts_windows_utf8_bom(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resource.json"
            path.write_text(json.dumps(resource().model_dump(mode="json")), encoding="utf-8-sig")
            self.assertEqual(load_resource(path).resource_id, "test-only")


if __name__ == "__main__":
    unittest.main()
