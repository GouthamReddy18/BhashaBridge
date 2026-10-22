"""Opt-in Google Cloud Translation Basic (v2) adapter using the standard library."""
from __future__ import annotations

import json
import math
import os
import socket
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.services.translation import (
    ProviderTranslation,
    TranslationConfiguration,
    TranslationInput,
    TranslationProviderFailure,
)

ENDPOINT = "https://translation.googleapis.com/language/translate/v2"
PROVIDER_ID = "google.cloud.translation.basic.v2"
DEFAULT_TIMEOUT_SECONDS = 10.0
MAX_BASIC_REQUEST_BYTES = 100_000
MAX_RESPONSE_BYTES = 1_000_000


@dataclass(frozen=True)
class ProviderReadiness:
    status: str
    detail: str


def _configuration(environ: dict[str, str] | os._Environ[str] | None = None):
    values = os.environ if environ is None else environ
    enabled = values.get("BHASHABRIDGE_GOOGLE_TRANSLATE_ENABLED", "false").strip().casefold() == "true"
    api_key = values.get("BHASHABRIDGE_GOOGLE_TRANSLATE_API_KEY", "").strip()
    model = values.get("BHASHABRIDGE_GOOGLE_TRANSLATE_MODEL", "nmt").strip()
    raw_timeout = values.get("BHASHABRIDGE_GOOGLE_TRANSLATE_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)).strip()
    try:
        timeout = float(raw_timeout)
    except (TypeError, ValueError):
        timeout = math.nan
    return enabled, api_key, model, timeout


def google_translation_readiness(environ: dict[str, str] | os._Environ[str] | None = None) -> ProviderReadiness:
    enabled, api_key, model, timeout = _configuration(environ)
    if not enabled:
        return ProviderReadiness("not_configured", "Google Cloud Translation is disabled; no provider call will be made.")
    if not api_key:
        return ProviderReadiness("unavailable", "Translation is enabled but BHASHABRIDGE_GOOGLE_TRANSLATE_API_KEY is missing.")
    if model != "nmt":
        return ProviderReadiness("unavailable", "The Basic adapter supports only the configured NMT model value nmt.")
    if not math.isfinite(timeout) or timeout <= 0 or timeout > 120:
        return ProviderReadiness("unavailable", "Translation timeout must be a finite number greater than 0 and at most 120 seconds.")
    return ProviderReadiness("configured", "Google Cloud Translation Basic v2 is configured; a call occurs only for an explicit translation request.")


class GoogleCloudTranslationProvider:
    """Translation adapter. Tests inject an opener; production defaults to urllib."""

    provider_id = PROVIDER_ID
    supports_experiment_configuration = True

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "nmt",
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("api_key must be nonblank")
        if model != "nmt":
            raise ValueError("Google Cloud Translation Basic adapter supports only model nmt")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or not 0 < timeout_seconds <= 120
        ):
            raise ValueError("timeout_seconds must be finite, greater than 0, and at most 120")
        self._api_key = api_key.strip()
        self.requested_model = model
        self.timeout_seconds = timeout_seconds
        self._opener = opener

    def translate(self, request: TranslationInput) -> ProviderTranslation:
        return self._translate(request.text, target="en", model=self.requested_model)

    def translate_configured(
        self, request: TranslationInput, configuration: TranslationConfiguration
    ) -> ProviderTranslation:
        model = configuration.requested_model or self.requested_model
        settings = configuration.generation_settings or {}
        if configuration.target_language != "en" or model != self.requested_model or settings:
            raise TranslationProviderFailure("provider_configuration_error", attempted=False)
        return self._translate(request.text, target=configuration.target_language, model=model)

    def _translate(self, text: str, *, target: str, model: str) -> ProviderTranslation:
        if not isinstance(text, str) or not text.strip():
            raise TranslationProviderFailure("provider_request_error", attempted=False)
        body = json.dumps(
            {"q": text, "target": target, "format": "text", "model": model},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(body) > MAX_BASIC_REQUEST_BYTES:
            raise TranslationProviderFailure("provider_request_error", attempted=False)
        request = Request(
            ENDPOINT,
            data=body,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "X-Goog-Api-Key": self._api_key,
            },
            method="POST",
        )
        try:
            with self._opener(request, timeout=self.timeout_seconds) as response:
                response_bytes = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            error_status = ""
            error_reasons: set[str] = set()
            if exc.code in {403, 429}:
                try:
                    error_body = json.loads(exc.read(32_768).decode("utf-8"))
                    error = error_body.get("error", {}) if isinstance(error_body, dict) else {}
                    if isinstance(error, dict):
                        error_status = error.get("status", "") if isinstance(error.get("status", ""), str) else ""
                        raw_errors = error.get("errors", [])
                        if isinstance(raw_errors, list):
                            error_reasons = {
                                item.get("reason", "").casefold()
                                for item in raw_errors
                                if isinstance(item, dict) and isinstance(item.get("reason", ""), str)
                            }
                except Exception:
                    pass
            if exc.code == 429 or error_status == "RESOURCE_EXHAUSTED" or error_reasons.intersection({"dailylimitexceeded", "userratelimitexceeded"}):
                code = "provider_quota_error"
            elif exc.code in {401, 403}:
                code = "provider_auth_error"
            elif 400 <= exc.code < 500:
                code = "provider_request_error"
            else:
                code = "provider_error"
            raise TranslationProviderFailure(code) from None
        except (TimeoutError, socket.timeout):
            raise TranslationProviderFailure("provider_timeout") from None
        except URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise TranslationProviderFailure("provider_timeout") from None
            raise TranslationProviderFailure("provider_error") from None
        except Exception:
            raise TranslationProviderFailure("provider_error") from None

        if len(response_bytes) > MAX_RESPONSE_BYTES:
            raise TranslationProviderFailure("provider_response_error")
        try:
            payload = json.loads(response_bytes.decode("utf-8"))
            translations = payload["data"]["translations"]
            if not isinstance(translations, list) or len(translations) != 1:
                raise ValueError("expected one translation")
            item = translations[0]
            translated_text = item["translatedText"]
            confirmed_model = item.get("model")
            if not isinstance(translated_text, str) or not translated_text.strip():
                raise ValueError("translation text is empty")
            if confirmed_model is not None and confirmed_model != self.requested_model:
                raise ValueError("model metadata is invalid")
        except (UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            raise TranslationProviderFailure("provider_response_error") from None
        return ProviderTranslation(translated_text=translated_text, confirmed_model=confirmed_model)


def configured_google_translation_provider(
    environ: dict[str, str] | os._Environ[str] | None = None,
    *,
    opener: Callable[..., Any] = urlopen,
) -> GoogleCloudTranslationProvider | None:
    _, api_key, model, timeout = _configuration(environ)
    status = google_translation_readiness(environ)
    if status.status != "configured":
        return None
    return GoogleCloudTranslationProvider(api_key, model=model, timeout_seconds=timeout, opener=opener)
