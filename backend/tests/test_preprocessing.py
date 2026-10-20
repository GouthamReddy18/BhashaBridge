import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.analysis import AnalyzeRequest
from app.services.preprocessing import normalize_whitespace
from app.services.tokenization import tokenize

client = TestClient(app)


class PreprocessingTests(unittest.TestCase):
    def test_repeated_and_surrounding_whitespace(self):
        self.assertEqual(normalize_whitespace("  hello\t\n world  "), "hello world")

    def test_empty_and_whitespace_only_rejected(self):
        for value in ("", "  \t\n"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                AnalyzeRequest(text=value)
            self.assertEqual(client.post("/api/v1/analyze", json={"text": value}).status_code, 422)

    def test_english_romanized_and_telugu_words(self):
        for text in ("hello world", "nenu college ki vellanu", "\u0c28\u0c47\u0c28\u0c41 \u0c07\u0c02\u0c1f\u0c3f\u0c15\u0c3f \u0c35\u0c46\u0c33\u0c4d\u0c24\u0c3e\u0c28\u0c41"):
            with self.subTest(text=text):
                self.assertEqual([item.text for item in tokenize(text)], text.split())

    def test_mixed_script(self):
        text = "\u0c28\u0c47\u0c28\u0c41 college \u0c15\u0c3f"
        self.assertEqual([t.text for t in tokenize(text)], ["\u0c28\u0c47\u0c28\u0c41", "college", "\u0c15\u0c3f"])

    def test_punctuation_numbers_and_apostrophes(self):
        tokens = tokenize("It's 42, isn't it?")
        self.assertEqual([(t.text, t.kind) for t in tokens], [
            ("It's", "word"), ("42", "word"), (",", "punctuation"),
            ("isn't", "word"), ("it", "word"), ("?", "punctuation"),
        ])

    def test_indices_and_start_inclusive_end_exclusive_offsets(self):
        text = "Hi, 42!"
        tokens = tokenize(text)
        self.assertEqual([t.index for t in tokens], list(range(4)))
        for token in tokens:
            self.assertEqual(text[token.start:token.end], token.text)
        self.assertEqual((tokens[0].start, tokens[0].end), (0, 2))
        self.assertEqual((tokens[1].start, tokens[1].end), (2, 3))

    def test_astral_unicode_offsets_use_python_code_points_in_normalized_text(self):
        original = "\U0001f600   nenu"
        response = client.post("/api/v1/analyze", json={"text": original}).json()
        normalized = response["normalized_text"]
        self.assertEqual(normalized, "\U0001f600 nenu")
        token = response["tokens"][1]
        self.assertEqual((token["index"], token["text"], token["start"], token["end"]), (1, "nenu", 2, 6))
        self.assertEqual(normalized[token["start"]:token["end"]], "nenu")

    def test_original_text_preserved_and_offsets_use_normalized_text(self):
        original = "  nenu   college ki vellanu  "
        payload = client.post("/api/v1/analyze", json={"text": original}).json()
        self.assertEqual(payload["original_text"], original)
        self.assertEqual(payload["normalized_text"], "nenu college ki vellanu")
        for token in payload["tokens"]:
            self.assertEqual(payload["normalized_text"][token["start"]:token["end"]], token["text"])

    def test_oversized_input_rejected(self):
        self.assertEqual(client.post("/api/v1/analyze", json={"text": "x" * 2001}).status_code, 422)

    def test_default_input_limit_accepts_2000_characters(self):
        request = AnalyzeRequest(text="x" * 2000)
        self.assertEqual(len(request.text), 2000)

    def test_non_string_input_rejected(self):
        self.assertEqual(client.post("/api/v1/analyze", json={"text": 12}).status_code, 422)

    def test_health_and_readiness_preserved_and_updated_truthfully(self):
        self.assertEqual(client.get("/health").json(), {"status": "ok"})
        ready = client.get("/ready").json()
        self.assertFalse(ready["ready"])
        statuses = {m["name"]: m["status"] for m in ready["modules"]}
        self.assertEqual(statuses["normalization"], "available")
        self.assertEqual(statuses["tokenization"], "available")
        self.assertEqual(statuses["translation"], "not_configured")


if __name__ == "__main__":
    unittest.main()
