"""Shared schemas: classification, tags, summary, fallback fields, final envelope."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TAG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

DocumentType = Literal[
    "Vendor Contract", "Support Ticket", "Statement of Work", "Invoice", "Other"
]


class StrictBase(BaseModel):
    """Base for every schema in the pipeline: unknown keys are rejected."""

    model_config = ConfigDict(extra="forbid")


class Classification(StrictBase):
    """Classifier output: type, confidence, and justifying signals."""

    document_type: DocumentType
    confidence: float = Field(ge=0, le=1)
    signals: list[str] = Field(
        min_length=1,
        max_length=3,
        description="Short phrases from the document that justify the choice",
    )


class TagSet(StrictBase):
    """Tagger output. Format rules enforced at schema level so retries are rare."""

    tags: list[str] = Field(
        min_length=3,
        max_length=7,
        description="Lowercase hyphen-separated semantic tags grounded in the document",
    )

    @field_validator("tags")
    @classmethod
    def _format_and_uniqueness(cls, tags: list[str]) -> list[str]:
        for tag in tags:
            if not TAG_PATTERN.match(tag):
                raise ValueError(f"tag '{tag}' must match {TAG_PATTERN.pattern}")
        if len(set(tags)) != len(tags):
            raise ValueError("tags must be unique")
        return tags


class Summary(StrictBase):
    """Summarizer output."""

    summary: str = Field(description="2-3 plain-language sentences")


class PipelineMeta(StrictBase):
    """Run metadata attached to every output."""

    model_calls: int = 0
    retries: dict[str, int] = Field(default_factory=dict)
    validation_errors_fixed: list[str] = Field(default_factory=list)
    validation_errors_unresolved: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0


class FinalOutput(StrictBase):
    """The envelope written to output/<doc>.json."""

    source_file: str
    classification: Classification
    tags: list[str]
    extracted_fields: dict
    summary: str
    pipeline_meta: PipelineMeta
