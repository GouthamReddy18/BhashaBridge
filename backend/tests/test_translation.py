import unittest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.dependencies import get_translation_provider
from app.main import app
from app.schemas.analysis import TranslationResult
from app.services.translation import (
    MockTranslationProvider,
    ProviderTranslation,
    TranslationInput,
)


class FakeProvider:
    provider_id = "fake.local-test"
    _UNSET = object()

    def __init__(self, result=_UNSET, error=None):
        self.result = ProviderTranslation("fixture output") if result is self._UNSET else result
        self.error = error
        self.calls = []

    def translate(self, request: TranslationInput):
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return self.result


class BrokenIdProvider(FakeProvider):
    @property
    def provider_id(self):
        raise RuntimeError("private metadata")


class InvalidIdProvider(FakeProvider):
    provider_id = " "


class NonStringIdProvider(FakeProvider):
    provider_id = None


class TranslationIntegrationTests(unittest.TestCase):
    def request_with_provider(self, payload, provider):
        previous = app.dependency_overrides.get(get_translation_provider)
        app.dependency_overrides[get_translation_provider] = lambda: provider
        try:
            with TestClient(app) as client:
                return client.post("/api/v1/analyze", json=payload)
        finally:
            if previous is None:
                app.dependency_overrides.pop(get_translation_provider, None)
            else:
                app.dependency_overrides[get_translation_provider] = previous

    def test_not_requested_is_disabled_and_provider_is_not_called(self):
        provider = FakeProvider()
        response = self.request_with_provider({"text": "hello"}, provider)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["translation"], {"status": "disabled"})
        self.assertEqual(provider.calls, [])

    def test_requested_without_provider_is_unavailable(self):
        response = self.request_with_provider({"text": "hello", "translate": True}, None)
        self.assertEqual(response.status_code, 200)
        result = response.json()["translation"]
        self.assertEqual(result, {"status": "unavailable", "error_code": "provider_not_configured"})

    def test_success_records_provider_and_exact_original_input(self):
        source = "  nenu bank  "
        provider = FakeProvider(ProviderTranslation("fixture translation"))
        response = self.request_with_provider({"text": source, "translate": True}, provider)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["original_text"], source)
        self.assertEqual(body["normalized_text"], "nenu bank")
        self.assertEqual(provider.calls, [TranslationInput(text=source)])
        self.assertEqual(body["translation"], {
            "status": "success", "input_text": source,
            "provider_id": "fake.local-test", "translated_text": "fixture translation",
        })
        self.assertTrue(body["tokens"])
        self.assertIn("transliterations", body)
        self.assertIn("ambiguities", body)

    def test_provider_exception_is_safe_and_never_success(self):
        provider = FakeProvider(error=RuntimeError("secret provider detail"))
        response = self.request_with_provider({"text": "hello", "translate": True}, provider)
        self.assertEqual(response.status_code, 200)
        result = response.json()["translation"]
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_code"], "provider_error")
        self.assertNotIn("secret provider detail", response.text)
        self.assertNotIn("translated_text", result)

    def test_empty_and_malformed_provider_outputs_fail(self):
        for value in (ProviderTranslation("  "), None, {"translated_text": "made up"}):
            with self.subTest(output=value):
                provider = FakeProvider(value)
                response = self.request_with_provider({"text": "hello", "translate": True}, provider)
                result = response.json()["translation"]
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["error_code"], "invalid_provider_output")
                self.assertNotIn("translated_text", result)

    def test_provider_identifier_failure_is_failed_and_safe(self):
        for provider in (BrokenIdProvider(), InvalidIdProvider(), NonStringIdProvider()):
            with self.subTest(provider=type(provider).__name__):
                response = self.request_with_provider({"text": "hello", "translate": True}, provider)
                result = response.json()["translation"]
                self.assertEqual(result, {"status": "failed", "error_code": "provider_metadata_error"})
                self.assertNotIn("private metadata", response.text)

    def test_schema_accepts_unavailable_with_provider_not_configured(self):
        result = TranslationResult(status="unavailable", error_code="provider_not_configured")
        self.assertEqual(result.status, "unavailable")

    def test_schema_rejects_failed_with_provider_not_configured(self):
        with self.assertRaisesRegex(ValidationError, "failed translation requires a provider failure"):
            TranslationResult(
                status="failed", input_text="hello", provider_id="fake.provider",
                error_code="provider_not_configured",
            )

    def test_schema_accepts_failed_with_provider_failure_code(self):
        result = TranslationResult(
            status="failed", input_text="hello", provider_id="fake.provider",
            error_code="provider_error",
        )
        self.assertEqual(result.status, "failed")

    def test_schema_success_requires_valid_provider_id_and_no_error_code(self):
        valid = TranslationResult(
            status="success", input_text="hello", provider_id="fake.provider",
            translated_text="hola",
        )
        self.assertEqual(valid.status, "success")
        with self.assertRaisesRegex(ValidationError, "successful translation requires input, provider, and nonblank output"):
            TranslationResult(
                status="success", input_text="hello", provider_id=None,
                translated_text="hola",
            )
        with self.assertRaisesRegex(ValidationError, "successful translation requires input, provider, and nonblank output"):
            TranslationResult(
                status="success", input_text="hello", provider_id=" ",
                translated_text="hola",
            )
        with self.assertRaisesRegex(ValidationError, "successful translation cannot contain an error"):
            TranslationResult(
                status="success", input_text="hello", provider_id="fake.provider",
                translated_text="hola", error_code="provider_error",
            )

    def test_schema_accepts_null_provider_id_only_for_identification_failure(self):
        result = TranslationResult(
            status="failed", input_text="hello", provider_id=None,
            error_code="provider_metadata_error",
        )
        self.assertEqual(result.status, "failed")
        with self.assertRaisesRegex(ValidationError, "requires provider_metadata_error"):
            TranslationResult(
                status="failed", input_text="hello", provider_id=None,
                error_code="provider_error",
            )

    def test_unicode_translation_input_is_exact_and_analysis_offsets_are_preserved(self):
        source = "  \U0001f600   nenu \u0c28\u0c47\u0c28\u0c41  "
        provider = FakeProvider(ProviderTranslation("fixture output"))
        response = self.request_with_provider({"text": source, "translate": True}, provider)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(provider.calls, [TranslationInput(text=source)])
        self.assertEqual(body["translation"]["input_text"], source)
        self.assertEqual(body["original_text"], source)
        self.assertEqual(body["normalized_text"], "\U0001f600 nenu \u0c28\u0c47\u0c28\u0c41")
        self.assertEqual(body["tokens"][1]["text"], "nenu")
        self.assertEqual((body["tokens"][1]["start"], body["tokens"][1]["end"]), (2, 6))
        for token in body["tokens"]:
            self.assertEqual(body["normalized_text"][token["start"]:token["end"]], token["text"])
        baseline = self.request_with_provider({"text": body["normalized_text"]}, None).json()
        for field in ("tokens", "transliterations", "ambiguities"):
            self.assertEqual(body[field], baseline[field])

    def test_mock_provider_is_explicitly_test_output(self):
        result = MockTranslationProvider().translate(TranslationInput("hello"))
        self.assertEqual(MockTranslationProvider.provider_id, "mock.test")
        self.assertIn("NOT A TRANSLATION", result.translated_text)

    def test_invalid_translation_flag_uses_request_validation(self):
        response = self.request_with_provider({"text": "hello", "translate": "yes"}, None)
        self.assertEqual(response.status_code, 422)
        response = self.request_with_provider({"text": "hello", "unexpected": True}, None)
        self.assertEqual(response.status_code, 422)

    def test_translation_failure_preserves_existing_analysis_fields(self):
        baseline = self.request_with_provider({"text": "nenu bank"}, None).json()
        failed = self.request_with_provider({"text": "nenu bank", "translate": True}, FakeProvider(error=ValueError("x"))).json()
        for key in ("original_text", "normalized_text", "tokens", "transliterations", "ambiguities"):
            self.assertEqual(failed[key], baseline[key])
        self.assertEqual(failed["translation"]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
