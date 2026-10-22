"""Versioned, provenance-bearing linguistic resource records."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, model_validator

ResourceLanguage = Literal["TELUGU_ROMANIZED", "TELUGU_SCRIPT", "ENGLISH"]


class LinguisticRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: StrictStr = Field(min_length=1, max_length=128)
    rule_version: StrictStr = Field(min_length=1, max_length=64)
    source_surface: StrictStr = Field(min_length=1, max_length=200)
    source_language: ResourceLanguage
    replacement: StrictStr = Field(min_length=1, max_length=500)
    replacement_language: ResourceLanguage
    applicability: StrictStr = Field(min_length=1, max_length=1000)
    provenance: StrictStr = Field(min_length=1, max_length=2000)
    evidence_references: tuple[StrictStr, ...] = Field(min_length=1, max_length=20)
    review_status: Literal["pending", "reviewed", "rejected"]
    reviewer_id: StrictStr | None = None
    reviewed_at: StrictStr | None = None
    entity_preservation: Literal["confirmed_non_entity", "preserve_entity", "uncertain"]

    @model_validator(mode="after")
    def review_metadata_matches_status(self):
        if not all(value.strip() for value in (self.rule_id, self.rule_version,
            self.source_surface, self.replacement, self.applicability,
            self.provenance, *self.evidence_references)):
            raise ValueError("resource strings and evidence references must be nonblank")
        if self.review_status == "reviewed":
            if not self.reviewer_id or not self.reviewer_id.strip() or not self.reviewed_at or not self.reviewed_at.strip():
                raise ValueError("reviewed resources require reviewer_id and reviewed_at")
            try:
                if date.fromisoformat(self.reviewed_at).isoformat() != self.reviewed_at:
                    raise ValueError("reviewed_at must use YYYY-MM-DD")
            except ValueError as exc:
                raise ValueError("reviewed_at must be a valid YYYY-MM-DD date") from exc
        elif self.reviewer_id is not None or self.reviewed_at is not None:
            raise ValueError("pending or rejected resources cannot claim completed review metadata")
        return self


class LinguisticResourceManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    resource_id: StrictStr = Field(min_length=1, max_length=128)
    resource_version: StrictStr = Field(min_length=1, max_length=64)
    provenance: StrictStr = Field(min_length=1, max_length=2000)
    language_coverage: tuple[ResourceLanguage, ...] = Field(min_length=1)
    rules: tuple[LinguisticRule, ...] = ()

    @model_validator(mode="after")
    def validate_resource(self):
        if not all(value.strip() for value in (self.resource_id, self.resource_version, self.provenance)):
            raise ValueError("resource metadata must be nonblank")
        if self.language_coverage != tuple(sorted(set(self.language_coverage))):
            raise ValueError("language_coverage must be unique and sorted")
        ids = [rule.rule_id for rule in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("rule IDs must be unique within a resource")
        if any(rule.source_language not in self.language_coverage for rule in self.rules):
            raise ValueError("each rule source language must be covered by the resource")
        return self
