"""Selective Romanized Telugu transliteration with an offline-safe engine seam."""

from __future__ import annotations

import os
import unicodedata
from typing import Protocol

from app.schemas.analysis import AnalyzedToken, LanguageLabel, TransliterationResult


class TransliterationEngine(Protocol):
    """An explicitly supplied local engine; implementations must not fetch assets."""

    engine_id: str

    def transliterate(self, text: str) -> str | None: ...


def _enabled_from_environment() -> bool:
    return os.getenv("BHASHABRIDGE_TRANSLITERATION_ENABLED", "false").strip().casefold() in {"1", "true", "yes", "on"}


def configured_transliteration_status(*, enabled: bool | None = None) -> tuple[str, str]:
    """Report configuration only; do not inspect assets or initialize an engine."""
    is_enabled = _enabled_from_environment() if enabled is None else enabled
    if not is_enabled:
        return "not_configured", "Transliteration is disabled by default."
    return (
        "unavailable",
        "Transliteration is enabled, but no verified offline engine is configured; no engine was initialized.",
    )


def _is_telugu_candidate(value: object) -> bool:
    """Accept only Telugu Unicode letters and marks, with at least one letter.

    Every character must be in U+0C00..U+0C7F and have Unicode category L* or
    M*. This rejects whitespace, digits, punctuation, symbols, joiners, and
    other scripts. Nothing is stripped or repaired.
    """
    if not isinstance(value, str) or not value:
        return False
    categories = [unicodedata.category(char)[0] for char in value]
    return (
        any(category == "L" for category in categories)
        and all(0x0C00 <= ord(char) <= 0x0C7F and category in {"L", "M"}
                for char, category in zip(value, categories, strict=True))
    )


def transliterate_tokens(
    tokens: list[AnalyzedToken],
    *,
    enabled: bool | None = None,
    engine: TransliterationEngine | None = None,
) -> tuple[list[TransliterationResult], str, str]:
    """Return one trace record per token plus a module status and explanation.

    Only a TELUGU_ROMANIZED label is eligible. No engine is constructed here;
    this prevents an optional dependency from downloading models implicitly.
    """
    is_enabled = _enabled_from_environment() if enabled is None else enabled
    records: list[TransliterationResult] = []
    module_status, module_detail = configured_transliteration_status(enabled=is_enabled)

    if is_enabled and engine is not None:
        module_status = "available"
        module_detail = "An injected local transliteration engine is active for TELUGU_ROMANIZED tokens only."

    for token in tokens:
        label: LanguageLabel = token.language.label
        common = {
            "token_index": token.index,
            "original_surface": token.text,
            "start": token.start,
            "end": token.end,
            "detected_language": label,
        }
        if label != "TELUGU_ROMANIZED":
            records.append(TransliterationResult(
                **common, attempted=False, status="skipped",
                reason="Token language label is not TELUGU_ROMANIZED.",
            ))
        elif not is_enabled:
            records.append(TransliterationResult(
                **common, attempted=False, status="disabled",
                reason="Transliteration is disabled by configuration.",
            ))
        elif engine is None:
            records.append(TransliterationResult(
                **common, attempted=False, status="unavailable",
                reason="No verified offline transliteration engine is configured.",
            ))
        else:
            try:
                candidate = engine.transliterate(token.text)
            except Exception as exc:
                engine_error = f"Engine raised {type(exc).__name__}."
                candidate = None
            else:
                engine_error = None

            try:
                engine_id = engine.engine_id
            except Exception as exc:
                records.append(TransliterationResult(
                    **common, attempted=True, status="failed",
                    reason=f"Engine metadata access failed ({type(exc).__name__}).",
                ))
                continue

            if engine_error is not None:
                records.append(TransliterationResult(
                    **common, attempted=True, engine_id=engine_id,
                    status="failed", reason=engine_error,
                ))
            elif _is_telugu_candidate(candidate):
                records.append(TransliterationResult(
                    **common, attempted=True, candidate=candidate,
                    engine_id=engine_id, status="succeeded",
                    reason="Engine returned a non-empty Telugu-script candidate.",
                ))
            else:
                records.append(TransliterationResult(
                    **common, attempted=True, engine_id=engine_id,
                    status="failed", reason="Engine returned no valid Telugu-script candidate.",
                ))
    return records, module_status, module_detail
