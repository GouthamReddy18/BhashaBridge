"""Token-level LID baseline and optional local IndicLID FastText adapter."""

from __future__ import annotations

import importlib.util
import os
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.schemas.analysis import LanguageAnnotation, Token

# Small, transparent seed lists only. These are rules, not a trained model.
ROMANIZED_TELUGU_WORDS = frozenset({
    "nenu", "nuvvu", "meeru", "manam", "memu", "vallu", "adi", "idi",
    "ki", "lo", "nundi", "daggara", "ayyaka", "intiki", "vellanu",
    "velthanu", "vastanu", "cheyyi", "cheyyali", "undi", "kaadu",
})
ENGLISH_SEED_WORDS = frozenset({
    "hello", "please", "the", "and", "is", "are", "with", "for",
    "college", "meeting", "account", "open", "wait", "bank",
})
TELUGU_BLOCK_START = 0x0C00
TELUGU_BLOCK_END = 0x0C7F


class TokenLanguageIdentifier(Protocol):
    def identify(self, tokens: list[Token]) -> list[LanguageAnnotation]: ...


@dataclass(frozen=True)
class IdentifierStatus:
    name: str
    status: str
    detail: str


class RuleBasedTokenLanguageIdentifier:
    """Conservative script/category rules plus small exact-match seed lexicons."""

    def identify(self, tokens: list[Token]) -> list[LanguageAnnotation]:
        return [self._identify_token(token) for token in tokens]

    @staticmethod
    def _identify_token(token: Token) -> LanguageAnnotation:
        if token.kind == "punctuation":
            return LanguageAnnotation(label="PUNCTUATION", method="tokenizer_rule", evidence="Tokenizer marked this surface as punctuation or a symbol.")

        if token.text and all(unicodedata.category(char)[0] == "N" for char in token.text):
            return LanguageAnnotation(label="NUMBER", method="unicode_category_rule", evidence="All token characters have a Unicode number category.")

        letters_and_marks = [char for char in token.text if unicodedata.category(char)[0] in {"L", "M"}]
        if letters_and_marks and all(TELUGU_BLOCK_START <= ord(char) <= TELUGU_BLOCK_END for char in letters_and_marks):
            return LanguageAnnotation(label="TELUGU_SCRIPT", method="unicode_script_rule", evidence="Letters/marks use the Telugu Unicode block; this detects script, not guaranteed language.")

        normalized = token.text.casefold()
        if normalized in ROMANIZED_TELUGU_WORDS:
            return LanguageAnnotation(label="TELUGU_ROMANIZED", method="romanized_telugu_seed_lexicon", evidence="Exact match in the small documented Romanized Telugu seed lexicon.")
        if normalized in ENGLISH_SEED_WORDS:
            return LanguageAnnotation(label="ENGLISH", method="english_seed_lexicon", evidence="Exact match in the small documented English seed lexicon.")

        if letters_and_marks and not any(ord(char) < 128 and char.isalpha() for char in letters_and_marks) and not all(TELUGU_BLOCK_START <= ord(char) <= TELUGU_BLOCK_END for char in letters_and_marks):
            return LanguageAnnotation(label="OTHER", method="unsupported_script_rule", evidence="Alphabetic token uses a script outside this Telugu-English baseline; language is not identified.")

        return LanguageAnnotation(label="UNKNOWN", method="abstention", evidence="No supported script or exact lexicon evidence; no language guessed from position or Latin script alone.")


class IndicLIDFastTextTokenIdentifier:
    """Optional local FTN/FTR models applied independently to each token.

    IndicLID's documented task is sentence-level. Per-token calls are an adapter
    experiment and are not claimed to be validated for short/mixed tokens.
    """

    def __init__(self, native_model_path: str, roman_model_path: str):
        import fasttext  # Optional dependency, imported only when explicitly configured.

        self.native_model = fasttext.load_model(native_model_path)
        self.roman_model = fasttext.load_model(roman_model_path)
        self.baseline = RuleBasedTokenLanguageIdentifier()

    def identify(self, tokens: list[Token]) -> list[LanguageAnnotation]:
        output: list[LanguageAnnotation] = []
        for token in tokens:
            rule = self.baseline._identify_token(token)
            if rule.label in {"PUNCTUATION", "NUMBER"}:
                output.append(rule)
                continue
            script_chars = [c for c in token.text if unicodedata.category(c)[0] in {"L", "M"}]
            roman = all(ord(c) < 128 for c in script_chars) if script_chars else True
            model = self.roman_model if roman else self.native_model
            model_name = "IndicLID-FTR" if roman else "IndicLID-FTN"
            try:
                labels, scores = model.predict(token.text, k=1)
                code = labels[0].removeprefix("__label__")
                score = float(scores[0])
            except Exception as exc:
                output.append(LanguageAnnotation(label="UNKNOWN", method="indic_lid_error", evidence=f"Configured model prediction failed ({type(exc).__name__}); abstained."))
                continue
            mapped = {"tel_Telu": "TELUGU_SCRIPT", "tel_Latn": "TELUGU_ROMANIZED", "eng_Latn": "ENGLISH", "other": "OTHER"}.get(code, "OTHER")
            if score < 0.6:
                output.append(LanguageAnnotation(label="UNKNOWN", method=model_name, evidence=f"Top model label {code} was below the configured 0.6 threshold." , confidence=score))
            else:
                output.append(LanguageAnnotation(label=mapped, method=model_name, evidence=f"Independent token input predicted IndicLID class {code}; single-token use is not validated for this task.", confidence=score))
        return output


@lru_cache(maxsize=4)
def _load_local_indiclid(native_path: str, roman_path: str) -> IndicLIDFastTextTokenIdentifier:
    return IndicLIDFastTextTokenIdentifier(native_path, roman_path)


def _provider_config() -> tuple[str, str, str]:
    return (
        os.getenv("BHASHABRIDGE_LID_PROVIDER", "baseline").strip().casefold(),
        os.getenv("BHASHABRIDGE_INDICLID_FTN_PATH", "").strip(),
        os.getenv("BHASHABRIDGE_INDICLID_FTR_PATH", "").strip(),
    )


def configured_model_status(*, loaded: bool = False, error: str | None = None) -> IdentifierStatus:
    provider, native_path, roman_path = _provider_config()
    if provider == "baseline":
        return IdentifierStatus("indic_lid_model", "not_configured", "Optional IndicLID is disabled. No model is loaded or downloaded.")
    if provider != "indic_lid":
        return IdentifierStatus("indic_lid_model", "unavailable", "Unknown BHASHABRIDGE_LID_PROVIDER value; use baseline or indic_lid.")
    if not native_path or not roman_path or not Path(native_path).is_file() or not Path(roman_path).is_file():
        return IdentifierStatus("indic_lid_model", "unavailable", "Provider requested, but local FTN/FTR model paths are missing or do not exist; no download was attempted.")
    if importlib.util.find_spec("fasttext") is None:
        return IdentifierStatus("indic_lid_model", "not_installed", "Local models are configured, but optional fasttext is not installed.")
    if error:
        return IdentifierStatus("indic_lid_model", "unavailable", f"Local model could not be loaded ({error}); baseline remains active.")
    if loaded:
        return IdentifierStatus("indic_lid_model", "available", "Local IndicLID FTN/FTR models loaded; predictions are made independently per token and are not validated for code-mixed token use.")
    return IdentifierStatus("indic_lid_model", "configured", "Local FTN/FTR paths and fasttext are present; models load lazily on the first analyze request. No download occurs.")


def resolve_identifier() -> tuple[TokenLanguageIdentifier, IdentifierStatus]:
    provider, native_path, roman_path = _provider_config()
    if provider != "indic_lid":
        return RuleBasedTokenLanguageIdentifier(), configured_model_status()
    status = configured_model_status()
    if status.status in {"unavailable", "not_installed"}:
        return RuleBasedTokenLanguageIdentifier(), status
    try:
        identifier = _load_local_indiclid(str(Path(native_path).resolve()), str(Path(roman_path).resolve()))
    except Exception as exc:
        return RuleBasedTokenLanguageIdentifier(), configured_model_status(error=type(exc).__name__)
    return identifier, configured_model_status(loaded=True)
