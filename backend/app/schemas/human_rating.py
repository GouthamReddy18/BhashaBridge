"""Human semantic-preservation judgment artifact records."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator


class HumanRatingRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    rubric_version: Literal["semantic-preservation-0-4.v1"]
    example_id: StrictStr = Field(min_length=1, max_length=200)
    arm: Literal["direct", "assisted"] | None = None
    display_label: Literal["A", "B"] | None = None
    rating: StrictInt | None = Field(default=None, ge=0, le=4)
    status: Literal["pending", "complete"] = "pending"
    reviewer_id: StrictStr | None = None
    reviewer_provenance: StrictStr | None = None
    reviewed_at: StrictStr | None = None
    uncertainty_note: StrictStr | None = None

    @model_validator(mode="after")
    def validate_completion(self):
        if bool(self.arm) == bool(self.display_label):
            raise ValueError("exactly one of arm or display_label is required")
        if not self.example_id.strip():
            raise ValueError("example_id must be nonblank")
        if self.status == "pending":
            if any(value is not None for value in (self.rating, self.reviewer_id, self.reviewer_provenance, self.reviewed_at)):
                raise ValueError("pending ratings cannot contain a judgment or completed review metadata")
        else:
            if self.rating is None or not self.reviewer_id or not self.reviewer_id.strip():
                raise ValueError("complete ratings require a 0-4 score and reviewer_id")
            if not self.reviewer_provenance or not self.reviewer_provenance.strip():
                raise ValueError("complete ratings require reviewer provenance")
            if not self.reviewed_at or not self.reviewed_at.strip():
                raise ValueError("complete ratings require reviewed_at")
            try:
                if date.fromisoformat(self.reviewed_at).isoformat() != self.reviewed_at:
                    raise ValueError
            except ValueError:
                raise ValueError("reviewed_at must be a valid YYYY-MM-DD date") from None
        return self
