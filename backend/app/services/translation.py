"""Synchronous provider seam; no network code, timeout, or cancellation boundary exists yet."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Protocol

from app.schemas.analysis import TranslationResult

_SAFE_MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
_SECRET_MARKER = re.compile(r"(?:api.?key|secret|token|password|^sk-)", re.IGNORECASE)


@dataclass(frozen=True)
class TranslationInput:
    """Exact text passed to a provider. Analysis passes original request text."""

    text: str


@dataclass(frozen=True)
class ProviderTranslation:
    """Provider-returned text without inferred confidence or diagnostics."""

    translated_text: str
    confirmed_model: str | None = None


@dataclass(frozen=True)
class TranslationConfiguration:
    """Requested settings for providers that explicitly support them."""

    target_language: str = "en"
    requested_model: str | None = None
    generation_settings: Mapping[str, str | int | float | bool] | None = None


class TranslationProviderFailure(Exception):
    """Safe provider failure category; never carries response text or secrets."""

    def __init__(self, error_code: str, *, attempted: bool = True):
        self.error_code = error_code
        self.attempted = attempted
        super().__init__(error_code)


class TranslationProvider(Protocol):
    """Translate explicit input and expose a stable provider identifier."""

    @property
    def provider_id(self) -> str: ...

    def translate(self, request: TranslationInput) -> ProviderTranslation: ...


class ConfigurableTranslationProvider(TranslationProvider, Protocol):
    """Optional capability for receiving and confirming experiment settings."""

    requested_model: str

    def translate_configured(
        self, request: TranslationInput, configuration: TranslationConfiguration
    ) -> ProviderTranslation: ...


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
    configuration: TranslationConfiguration | None = None,
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

    supports_configuration = callable(getattr(provider, "translate_configured", None))
    if configuration is not None and supports_configuration:
        forwarded = True
    else:
        forwarded = False
    try:
        request = TranslationInput(text=text)
        if forwarded:
            result = provider.translate_configured(request, configuration)
        else:
            result = provider.translate(request)
    except TranslationProviderFailure as exc:
        return TranslationResult(
            status="failed", input_text=text if exc.attempted else None, provider_id=provider_id,
            error_code=exc.error_code,
            provider_configuration_forwarded=True if forwarded else None,
        )
    except Exception:
        return TranslationResult(
            status="failed", input_text=text, provider_id=provider_id,
            error_code="provider_error",
            provider_configuration_forwarded=True if forwarded else None,
        )

    if (
        not isinstance(result, ProviderTranslation)
        or not isinstance(result.translated_text, str)
        or not result.translated_text.strip()
        or (result.confirmed_model is not None and (
            not isinstance(result.confirmed_model, str)
            or not _SAFE_MODEL.fullmatch(result.confirmed_model)
            or _SECRET_MARKER.search(result.confirmed_model)
        ))
    ):
        return TranslationResult(
            status="failed", input_text=text, provider_id=provider_id,
            error_code="invalid_provider_output",
            provider_configuration_forwarded=True if forwarded else None,
        )
    return TranslationResult(
        status="success", input_text=text, provider_id=provider_id,
        translated_text=result.translated_text, provider_model=result.confirmed_model,
        provider_configuration_forwarded=True if forwarded else None,
    )
