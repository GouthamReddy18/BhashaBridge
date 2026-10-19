from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator, model_validator

MAX_INPUT_CHARS = 2000
LanguageLabel = Literal[
    "TELUGU_ROMANIZED", "TELUGU_SCRIPT", "ENGLISH", "PUNCTUATION",
    "NUMBER", "OTHER", "UNKNOWN",
]


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: StrictStr = Field(max_length=MAX_INPUT_CHARS)

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


class AnalyzeResponse(BaseModel):
    original_text: str
    normalized_text: str
    tokens: list[AnalyzedToken]
    transliterations: list[TransliterationResult]
    modules: list[ModuleStatus]
    ambiguities: list[AmbiguityRecord] = Field(default_factory=list)
