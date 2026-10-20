from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, field_validator, model_validator

MAX_INPUT_CHARS = 2000
LanguageLabel = Literal[
    "TELUGU_ROMANIZED", "TELUGU_SCRIPT", "ENGLISH", "PUNCTUATION",
    "NUMBER", "OTHER", "UNKNOWN",
]


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: StrictStr = Field(max_length=MAX_INPUT_CHARS)
    translate: StrictBool = False

    @field_validator("text")
    @classmethod
    def reject_empty_or_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must contain at least one non-whitespace character")
        return value


class LanguageAnnotation(BaseModel):
    label: LanguageLabel
    method: str
    evidence: str
    confidence: float | None = None


class Token(BaseModel):
    index: int
    text: str
    start: int
    end: int
    kind: Literal["word", "punctuation"]


class AnalyzedToken(Token):
    language: LanguageAnnotation


class TransliterationResult(BaseModel):
    token_index: int
    original_surface: str
    start: int
    end: int
    detected_language: LanguageLabel
    attempted: bool
    candidate: str | None = None
    engine_id: str | None = None
    status: Literal["skipped", "disabled", "succeeded", "failed", "unavailable"]
    reason: str


class AmbiguityCandidate(BaseModel):
    candidate_id: str
    description: str
    source: str


class AmbiguityRecord(BaseModel):
    """Resolved records select a listed candidate; abstentions select none."""

    token_index: int
    surface: str
    start: int
    end: int
    status: Literal["resolved", "abstained"]
    candidates: list[AmbiguityCandidate]
    selected_candidate: str | None = None
    rule_id: str
    evidence: str

    @model_validator(mode="after")
    def validate_selection(self) -> "AmbiguityRecord":
        candidate_ids = {candidate.candidate_id for candidate in self.candidates}
        if self.status == "resolved":
            if self.selected_candidate is None:
                raise ValueError("resolved ambiguity must select a candidate")
            if self.selected_candidate not in candidate_ids:
                raise ValueError("selected_candidate must identify a configured candidate")
        elif self.selected_candidate is not None:
            raise ValueError("abstained ambiguity must not select a candidate")
        return self


class ModuleStatus(BaseModel):
    name: str
    status: Literal["available", "configured", "not_installed", "not_configured", "unavailable", "not_implemented"]
    detail: str


class TranslationResult(BaseModel):
    """Outcome and exact provider input, when a provider was actually invoked."""

    status: Literal["disabled", "unavailable", "success", "failed"]
    input_text: str | None = None
    provider_id: str | None = None
    translated_text: str | None = None
    error_code: Literal[
        "provider_not_configured", "provider_metadata_error",
        "provider_error", "invalid_provider_output",
    ] | None = None

    @model_validator(mode="after")
    def validate_outcome(self) -> "TranslationResult":
        if self.status == "disabled":
            if any(value is not None for value in (self.input_text, self.provider_id, self.translated_text, self.error_code)):
                raise ValueError("disabled translation cannot contain provider data")
        elif self.status == "unavailable":
            if self.input_text is not None or self.provider_id is not None or self.translated_text is not None:
                raise ValueError("unavailable translation cannot claim provider input or output")
            if self.error_code != "provider_not_configured":
                raise ValueError("unavailable translation requires provider_not_configured")
        elif self.status == "success":
            if (
                self.input_text is None
                or self.provider_id is None
                or not self.provider_id.strip()
                or not self.translated_text
                or not self.translated_text.strip()
            ):
                raise ValueError("successful translation requires input, provider, and nonblank output")
            if self.error_code is not None:
                raise ValueError("successful translation cannot contain an error")
        else:
            if self.translated_text is not None or self.error_code is None or self.error_code == "provider_not_configured":
                raise ValueError("failed translation requires a provider failure and cannot contain output")
            if self.provider_id is None and self.error_code != "provider_metadata_error":
                raise ValueError("failed translation without a provider identifier requires provider_metadata_error")
            if self.provider_id is not None and not self.provider_id.strip():
                raise ValueError("failed translation provider identifier must be nonblank")
        return self


class AnalyzeResponse(BaseModel):
    original_text: str
    normalized_text: str
    tokens: list[AnalyzedToken]
    transliterations: list[TransliterationResult]
    modules: list[ModuleStatus]
    ambiguities: list[AmbiguityRecord] = Field(default_factory=list)
    translation: TranslationResult
