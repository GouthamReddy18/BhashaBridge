import json
import unittest
from io import BytesIO
from urllib.error import HTTPError

from app.schemas.experiment import ExperimentConfiguration
from app.services.experiment import run_paired_experiment
from app.services.google_translation import (
    GoogleCloudTranslationProvider,
    configured_google_translation_provider,
    google_translation_readiness,
)
from app.services.translation import TranslationConfiguration, TranslationInput, translate_text


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self, limit=-1):
        return self.payload[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class GoogleTranslationTests(unittest.TestCase):
    def test_readiness_requires_explicit_enable_and_key(self):
        self.assertEqual(google_translation_readiness({}).status, "not_configured")
        self.assertEqual(
            google_translation_readiness({"BHASHABRIDGE_GOOGLE_TRANSLATE_ENABLED": "true"}).status,
            "unavailable",
        )
        configured = {
            "BHASHABRIDGE_GOOGLE_TRANSLATE_ENABLED": "true",
            "BHASHABRIDGE_GOOGLE_TRANSLATE_API_KEY": "test-only-key",
        }
        self.assertEqual(google_translation_readiness(configured).status, "configured")
        self.assertIsNotNone(configured_google_translation_provider(configured, opener=lambda *_a, **_k: None))

    def test_readiness_rejects_unsupported_model_and_bad_timeout(self):
        base = {
            "BHASHABRIDGE_GOOGLE_TRANSLATE_ENABLED": "true",
            "BHASHABRIDGE_GOOGLE_TRANSLATE_API_KEY": "test-only-key",
        }
        self.assertEqual(
            google_translation_readiness(dict(base, BHASHABRIDGE_GOOGLE_TRANSLATE_MODEL="custom")).status,
            "unavailable",
        )
        self.assertEqual(
            google_translation_readiness(dict(base, BHASHABRIDGE_GOOGLE_TRANSLATE_TIMEOUT_SECONDS="nan")).status,
            "unavailable",
        )

    def test_request_uses_exact_unicode_plain_text_and_confirms_returned_model(self):
        captured = {}

        def opener(request, *, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse(json.dumps({
                "data": {"translations": [{"translatedText": "English result", "model": "nmt"}]}
            }).encode("utf-8"))

        provider = GoogleCloudTranslationProvider("test-secret", timeout_seconds=3, opener=opener)
        result = provider.translate(TranslationInput("తెలుగు nenu hi"))
        request = captured["request"]
        self.assertEqual(captured["timeout"], 3)
        self.assertEqual(request.full_url, "https://translation.googleapis.com/language/translate/v2")
        self.assertEqual(request.get_header("X-goog-api-key"), "test-secret")
        self.assertEqual(json.loads(request.data), {
            "q": "తెలుగు nenu hi", "target": "en", "format": "text", "model": "nmt"
        })
        self.assertEqual(result.translated_text, "English result")
        self.assertEqual(result.confirmed_model, "nmt")

    def test_paired_experiment_forwards_requested_model_and_records_confirmation(self):
        requests = []

        def opener(request, *, timeout):
            requests.append(json.loads(request.data))
            return FakeResponse(json.dumps({
                "data": {"translations": [{"translatedText": "English result", "model": "nmt"}]}
            }).encode("utf-8"))

        provider = GoogleCloudTranslationProvider("test-secret", opener=opener)
        result = run_paired_experiment("nenu", provider=provider)
        self.assertEqual(result.configuration.requested_model, "nmt")
        self.assertTrue(result.provider_configuration_forwarded)
        self.assertEqual(result.direct.provider_confirmed.model, "nmt")
        self.assertEqual(result.assisted.provider_confirmed.model, "nmt")
        self.assertEqual([row["target"] for row in requests], ["en", "en"])

    def test_timeout_maps_to_safe_timeout_code(self):
        provider = GoogleCloudTranslationProvider("test-secret", opener=lambda *_a, **_k: (_ for _ in ()).throw(TimeoutError()))
        result = translate_text("private input", requested=True, provider=provider)
        self.assertEqual(result.error_code, "provider_timeout")
        self.assertEqual(result.input_text, "private input")
        self.assertNotIn("TimeoutError", str(result))

    def test_http_failures_map_to_safe_categories_without_body_or_key(self):
        cases = ((401, "provider_auth_error"), (403, "provider_auth_error"), (429, "provider_quota_error"),
                 (400, "provider_request_error"), (500, "provider_error"))
        for status, expected in cases:
            def opener(*_args, **_kwargs):
                raise HTTPError("https://example.invalid/?key=test-secret", status, "private body", {}, BytesIO(b"secret response"))
            provider = GoogleCloudTranslationProvider("test-secret", opener=opener)
            with self.subTest(status=status):
                result = translate_text("private input", requested=True, provider=provider)
                self.assertEqual(result.error_code, expected)
                self.assertNotIn("test-secret", repr(result))
                self.assertNotIn("private body", repr(result))

    def test_malformed_or_unexpected_provider_response_is_rejected(self):
        for body in (b"not-json", b'{"data":{"translations":[]}}',
                     b'{"data":{"translations":[{"translatedText":"ok","model":"secret-token"}]}}'):
            provider = GoogleCloudTranslationProvider("test-secret", opener=lambda *_a, **_k: FakeResponse(body))
            with self.subTest(body=body):
                result = translate_text("source", requested=True, provider=provider)
                self.assertEqual(result.error_code, "provider_response_error")

    def test_oversized_response_is_rejected(self):
        provider = GoogleCloudTranslationProvider(
            "test-secret", opener=lambda *_a, **_k: FakeResponse(b"x" * 1_000_001)
        )
        result = translate_text("source", requested=True, provider=provider)
        self.assertEqual(result.error_code, "provider_response_error")

    def test_unsupported_experiment_configuration_is_rejected_before_network(self):
        calls = []
        provider = GoogleCloudTranslationProvider("test-secret", opener=lambda *_a, **_k: calls.append(True))
        result = translate_text(
            "source", requested=True, provider=provider,
            configuration=TranslationConfiguration(
                target_language="en", requested_model="unsupported", generation_settings={}
            ),
        )
        self.assertEqual(result.error_code, "provider_configuration_error")
        self.assertIsNone(result.input_text)
        self.assertTrue(result.provider_configuration_forwarded)
        self.assertEqual(calls, [])

    def test_paired_unsupported_model_records_pre_invocation_failure(self):
        calls = []
        provider = GoogleCloudTranslationProvider("test-secret", opener=lambda *_a, **_k: calls.append(True))
        result = run_paired_experiment(
            "nenu", provider=provider,
            configuration=ExperimentConfiguration(requested_model="unsupported"),
        )
        self.assertEqual(result.invocation_order, [])
        self.assertTrue(result.provider_configuration_forwarded)
        self.assertEqual(result.direct.translation.error_code, "provider_configuration_error")
        self.assertIsNone(result.direct.provider_input)
        self.assertEqual(calls, [])

    def test_request_size_is_rejected_without_network(self):
        calls = []
        provider = GoogleCloudTranslationProvider("test-secret", opener=lambda *_a, **_k: calls.append(True))
        result = translate_text("x" * 100_001, requested=True, provider=provider)
        self.assertEqual(result.error_code, "provider_request_error")
        self.assertIsNone(result.input_text)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
