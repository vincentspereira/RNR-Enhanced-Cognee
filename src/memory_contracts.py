"""Bounded evidence declarations; supplied claims never confer verification."""
from __future__ import annotations

from typing import Literal, Optional
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MemoryEvidence(BaseModel):
    """An actor's source description, kept apart from server-recorded provenance.

    Classification is independent of the project's dynamic memory category.
    Confidence describes the submitter's assessment, not service verification.
    Source links are reference text only and never trigger a network request.
    """
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    kind: Literal["unclassified", "fact", "preference", "decision", "inference", "summary"] = "unclassified"
    source_id: Optional[str] = Field(default=None, min_length=1, max_length=200)
    source_uri: Optional[str] = Field(default=None, min_length=1, max_length=2000)
    source_sha256: Optional[str] = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    span_start: Optional[int] = Field(default=None, ge=0)
    span_end: Optional[int] = Field(default=None, ge=0)
    confidence: Optional[float] = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def coherent_source(self):
        if (self.span_start is None) != (self.span_end is None):
            raise ValueError("Source spans require both start and end")
        if self.span_start is not None:
            if self.span_end <= self.span_start or not self.source_id:
                raise ValueError("Source spans require a source ID and an end after the start")
        if self.source_uri:
            uri = urlsplit(self.source_uri)
            if (uri.scheme not in ("https", "http") or not uri.hostname
                    or uri.username or uri.password or uri.query or uri.fragment
                    or any(ord(char) < 33 for char in self.source_uri)):
                raise ValueError("Source URI must be an HTTP(S) reference without credentials, query or fragment")
        return self


def evidence_declaration(value=None) -> dict:
    """Validate declarations and explicitly label their unverified authority."""
    parsed = MemoryEvidence.model_validate(value or {}).model_dump(exclude_none=True)
    return {"declaration": parsed, "authority": "actor_submitted_unverified"}
