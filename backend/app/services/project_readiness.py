"""Read-only research-readiness summary for the project UI."""
from __future__ import annotations

from pathlib import Path

from app.services.dataset_validation import validate_dataset
from app.services.evaluation_readiness import check_evaluation_readiness
from app.services.google_translation import PROVIDER_ID, google_translation_readiness
from app.services.transliteration import configured_transliteration_status

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ILLUSTRATIVE_DATASET = PROJECT_ROOT / "data" / "drafts" / "illustrative_examples.jsonl"


def _blocker_category(message: str) -> str:
    text = message.casefold()
    if "reference_translation" in text:
        return "Reviewed English reference translations are required."
    if "intended_meaning" in text:
        return "Reviewed intended meanings are required."
    if "provenance" in text or "source_reference" in text or "human contribution" in text:
        return "Human-contributed provenance and source references are required."
    if "review" in text:
        return "Human review and field-level review metadata are required."
    if "split_group" in text or "group" in text:
        return "Stable split groups are required for leakage control."
    if "split" in text:
        return "Valid train, validation, and test split assignments are required."
    if "duplicate" in text:
        return "Duplicate IDs or normalized source text must be resolved."
    return "Dataset structural or readiness requirements remain unmet."


def project_research_readiness(dataset_path: str | Path = ILLUSTRATIVE_DATASET) -> dict:
    """Summarize repository readiness without creating data or making provider calls."""
    structural = validate_dataset(dataset_path)
    readiness = check_evaluation_readiness(dataset_path)
    provider = google_translation_readiness()
    transliteration_status, transliteration_detail = configured_transliteration_status()
    blocker_categories = sorted({_blocker_category(issue.message) for issue in readiness.errors})
    structurally_valid = structural.valid and structural.records_examined > 0
    dataset_ready = readiness.ready
    provider_ready = provider.status == "configured"

    conditions = [
        {
            "id": "direct_v1",
            "status": "ready" if dataset_ready and provider_ready else "blocked",
            "reason": "Exact-source baseline; it still requires an eligible dataset and configured provider."
            if dataset_ready and provider_ready
            else "Requires an eligible reviewed dataset and a configured translation provider.",
        },
        {
            "id": "normalized_v1",
            "status": "blocked",
            "reason": "No qualified, reviewed Telugu-English linguistic normalizer is registered.",
        },
        {
            "id": "transliterated_v1",
            "status": "blocked",
            "reason": "A qualified normalizer and reviewed selective transliteration resource are required.",
        },
        {
            "id": "ambiguity_aware_v1",
            "status": "blocked",
            "reason": "All prior resources and reviewed, authorized contextual transformation rules are required.",
        },
    ]
    resources = [
        {
            "id": "normalizer",
            "status": "missing",
            "research_eligible": False,
            "detail": "Whitespace collapsing is available but does not qualify as linguistic normalization.",
        },
        {
            "id": "transliterator",
            "status": transliteration_status,
            "research_eligible": False,
            "detail": transliteration_detail,
        },
        {
            "id": "contextual_transformer",
            "status": "illustrative_only",
            "research_eligible": False,
            "detail": "The English bank rule is a fixture, not a reviewed Telugu-English resource.",
        },
    ]
    return {
        "research_ready": bool(dataset_ready and provider_ready and all(item["status"] == "ready" for item in conditions)),
        "dataset": {
            "name": Path(dataset_path).name,
            "structural_status": "valid" if structurally_valid else "invalid_or_unavailable",
            "evaluation_status": "ready" if dataset_ready else "not_ready",
            "records_examined": readiness.records_examined,
            "structural_errors": len(structural.errors),
            "blocking_errors": len(readiness.errors),
            "warnings": len(readiness.warnings),
            "blocker_categories": blocker_categories,
        },
        "provider": {
            "provider_id": PROVIDER_ID,
            "status": provider.status,
            "detail": provider.detail,
        },
        "resources": resources,
        "conditions": conditions,
        "evaluation_reports": {
            "status": "not_catalogued",
            "detail": "Evaluation artifacts are explicit CLI inputs; no persistent report catalog is configured.",
        },
    }
