"""Synchronous provider seam; no network code, timeout, or cancellation boundary exists yet."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas.analysis import TranslationResult


@dataclass(frozen=True)
class TranslationInput:
    """Exact text passed to a provider. Analysis passes original request text."""

    text: str


@dataclass(frozen=True)
class ProviderTranslation:
    """Provider-returned text without inferred confidence or diagnostics."""

    translated_text: str


class TranslationProvider(Protocol):
    """Translate explicit input and expose a stable provider identifier."""

    @property
    def provider_id(self) -> str: ...

    def translate(self, request: TranslationInput) -> ProviderTranslation: ...


class MockTranslationProvider:
    """Deterministic test/demo output; this is not a linguistic translation."""

    provider_id = "mock.test"

    def translate(self, request: TranslationInput) -> ProviderTranslation:
        return ProviderTranslation(f"[MOCK OUTPUT - NOT A TRANSLATION] {request.text}")


def translate_text(
    text: str,
    *,
    requested: bool,
    provider: TranslationProvider | None,
) -> TranslationResult:
    """Invoke an injected provider safely and report an explicit outcome."""
    if not requested:
        return TranslationResult(status="disabled")
    if provider is None:
        return TranslationResult(status="unavailable", error_code="provider_not_configured")

    try:
        provider_id = provider.provider_id
    except Exception:
        return TranslationResult(status="failed", error_code="provider_metadata_error")
    if not isinstance(provider_id, str) or not provider_id.strip():
        return TranslationResult(status="failed", error_code="provider_metadata_error")

    try:
        result = provider.translate(TranslationInput(text=text))
    except Exception:
        return TranslationResult(
            status="failed", input_text=text, provider_id=provider_id,
            error_code="provider_error",
        )

    if not isinstance(result, ProviderTranslation) or not isinstance(result.translated_text, str) or not result.translated_text.strip():
        return TranslationResult(
            status="failed", input_text=text, provider_id=provider_id,
            error_code="invalid_provider_output",
        )
    return TranslationResult(
        status="success", input_text=text, provider_id=provider_id,
        translated_text=result.translated_text,
    )
