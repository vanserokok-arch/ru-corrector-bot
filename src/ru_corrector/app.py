"""FastAPI application for Russian text correction service."""

import time
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from .config import config
from .logging_config import get_logger, set_request_id, setup_logging
from .services.core_corrector import correct_text

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title=config.APP_NAME,
    description="Russian text correction service with LanguageTool and typography rules",
    version="1.0.0",
    debug=config.DEBUG,
)


class CorrectionRequest(BaseModel):
    """Request model for text correction."""

    text: str = Field(..., description="Text to correct", min_length=1)
    show_diff: bool = Field(default=False, description="Return HTML diff view")
    mode: Literal["min", "biz", "acad"] = Field(
        default="min", description="Correction mode: min (minimal), biz (business), acad (academic)"
    )

    @field_validator("text")
    @classmethod
    def validate_text_length(cls, v: str) -> str:
        """Validate text length."""
        if len(v) > config.MAX_TEXT_LEN:
            raise ValueError(f"Text too long. Maximum length is {config.MAX_TEXT_LEN} characters")
        return v


class CorrectionStats(BaseModel):
    """Statistics about the correction."""

    length: int = Field(..., description="Length of corrected text")
    changes: int = Field(..., description="Number of changes made")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")


class CorrectionResponse(BaseModel):
    """Response model for text correction."""

    original: str = Field(..., description="Original text")
    corrected: str = Field(..., description="Corrected text")
    diff: str | None = Field(None, description="HTML diff view if requested")
    stats: CorrectionStats = Field(..., description="Correction statistics")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")


@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    """Add request_id to each request."""
    request_id = set_request_id()
    request.state.request_id = request_id

    start_time = time.time()
    response = await call_next(request)
    duration = (time.time() - start_time) * 1000

    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration:.2f}ms")

    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors."""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=400,
        content={"error": "Validation error", "detail": str(exc)},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "An unexpected error occurred"},
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns service status and version.
    """
    return HealthResponse(status="ok", version="1.0.0")


@app.post("/correct", response_model=CorrectionResponse)
async def correct_endpoint(request: CorrectionRequest):
    """
    Correct Russian text.

    Applies LanguageTool corrections, custom typography rules, and optional styling.

    - **text**: Text to correct (required, max 15000 characters)
    - **show_diff**: Return HTML diff view (optional, default: false)
    - **mode**: Correction mode - min/biz/acad (optional, default: min)

    Returns corrected text with statistics.
    """
    logger.info(
        f"Correction request: mode={request.mode}, "
        f"text_length={len(request.text)}, show_diff={request.show_diff}"
    )

    start_time = time.time()

    try:
        if request.show_diff:
            corrected, diff_html = correct_text(
                request.text, mode=request.mode, do_typograph=True, make_diff_view=True
            )
        else:
            corrected = correct_text(
                request.text, mode=request.mode, do_typograph=True, make_diff_view=False
            )
            diff_html = None

        processing_time = (time.time() - start_time) * 1000

        # Calculate number of changes (simple diff count)
        changes = sum(1 for a, b in zip(request.text, corrected, strict=False) if a != b)
        changes += abs(len(request.text) - len(corrected))

        stats = CorrectionStats(
            length=len(corrected), changes=changes, processing_time_ms=round(processing_time, 2)
        )

        return CorrectionResponse(
            original=request.text, corrected=corrected, diff=diff_html, stats=stats
        )

    except Exception as e:
        logger.error(f"Error during correction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing text correction") from e


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting {config.APP_NAME} on {config.HOST}:{config.PORT}")
    uvicorn.run(
        "ru_corrector.app:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
    )
