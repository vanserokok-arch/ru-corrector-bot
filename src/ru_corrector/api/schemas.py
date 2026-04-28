"""API request and response schemas."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from ..config import config


class Edit(BaseModel):
    """Represents a single edit/correction made to text."""

    offset: int = Field(..., description="Character offset where edit starts")
    length: int = Field(..., description="Length of text being replaced")
    original: str = Field(..., description="Original text")
    replacement: str = Field(..., description="Replacement text")
    message: str = Field(default="", description="Explanation of the correction")


class Stats(BaseModel):
    """Statistics about the correction process."""

    chars_count: int = Field(..., description="Number of characters in result")
    edits_count: int = Field(..., description="Number of edits made")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")


class CorrectionRequest(BaseModel):
    """Request model for text correction."""

    text: str = Field(..., description="Text to correct", min_length=1)
    mode: Literal["base", "legal", "strict"] = Field(
        default="legal", description="Correction mode: base (minimal), legal (default), strict (aggressive)"
    )
    return_edits: bool = Field(default=True, description="Return list of edits made")

    @field_validator("text")
    @classmethod
    def validate_text_length(cls, v: str) -> str:
        """Reject text that exceeds the configured maximum length.

        Uses ``len(v)`` which counts Unicode code points, consistent with how
        ``config.MAX_TEXT_LEN`` is described ("characters").
        """
        if len(v) > config.MAX_TEXT_LEN:
            raise ValueError(
                f"Text too long: {len(v)} characters. Maximum allowed is {config.MAX_TEXT_LEN}."
            )
        return v


class CorrectionResponse(BaseModel):
    """Response model for text correction."""

    result: str = Field(..., description="Corrected text")
    edits: list[Edit] = Field(default_factory=list, description="List of edits made")
    stats: Stats = Field(..., description="Processing statistics")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
