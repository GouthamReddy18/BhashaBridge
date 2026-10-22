"""Offline validation and deterministic matching for reviewed resource manifests.

Review fields are supplied claims; this module does not authenticate people or
evidence. No production registry is bundled, so matching is infrastructure only.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.schemas.linguistic_resource import LinguisticResourceManifest, LinguisticRule


class ResourceError(ValueError):
    pass


def load_resource(path: str | Path) -> LinguisticResourceManifest:
    try:
        # PowerShell's common UTF-8 writer emits a BOM; accept it explicitly.
        raw = json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=_unique_object)
        return LinguisticResourceManifest.model_validate(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise ResourceError(f"invalid linguistic resource: {type(exc).__name__}") from None


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def resource_readiness(resource: LinguisticResourceManifest) -> tuple[str, ...]:
    """Return canonical blockers; reviewed declarations are not authenticated."""
    blockers: list[str] = []
    if not resource.rules:
        blockers.append("resource:no_rules_available")
    for rule in resource.rules:
        if rule.review_status == "pending":
            blockers.append(f"{rule.rule_id}:review_pending")
        elif rule.review_status == "rejected":
            blockers.append(f"{rule.rule_id}:review_rejected")
        if rule.entity_preservation != "confirmed_non_entity":
            blockers.append(f"{rule.rule_id}:entity_preservation_unconfirmed")
    return tuple(sorted(blockers))


def match_rule(
    resource: LinguisticResourceManifest,
    *, token_surface: str,
    token_language: str,
    applicable: bool,
    entity_preserved: bool,
) -> LinguisticRule | None:
    """Exact-match only; fail closed for review, applicability, and entities."""
    if (type(applicable) is not bool or type(entity_preserved) is not bool
            or not applicable or not entity_preserved or resource_readiness(resource)
            or token_language not in {"TELUGU_ROMANIZED", "TELUGU_SCRIPT", "ENGLISH"}):
        return None
    matches = [rule for rule in resource.rules
        if rule.source_surface.casefold() == token_surface.casefold()
        and rule.source_language == token_language
        and rule.review_status == "reviewed"
        and rule.entity_preservation == "confirmed_non_entity"]
    return matches[0] if len(matches) == 1 else None
