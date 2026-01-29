"""FastAPI application for Russian text correction service."""

import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import field_validator

from .api.schemas import CorrectionRequest, CorrectionResponse, Edit, HealthResponse, Stats
from .config import config
from .core.engine import CorrectionEngine
from .logging_config import get_logger, set_request_id, setup_logging

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

# Initialize correction engine
engine = CorrectionEngine()


# Add validation to request model
def validate_text_length(v: str) -> str:
    """Validate text length."""
    if len(v) > config.MAX_TEXT_LEN:
        raise ValueError(f"Text too long. Maximum length is {config.MAX_TEXT_LEN} characters")
    return v


# Patch the request model with validation
CorrectionRequest.model_fields["text"].metadata = [
    field_validator("text")(classmethod(validate_text_length))
]


@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    """Add request_id to each request."""
    request_id = set_request_id()
    request.state.request_id = request_id

    start_time = time.time()
    response = await call_next(request)
    duration = (time.time() - start_time) * 1000

    logger.debug(f"{request.method} {request.url.path} - {response.status_code} - {duration:.2f}ms")

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

    Applies LanguageTool corrections, custom typography rules, and mode-specific formatting.

    - **text**: Text to correct (required, max 15000 characters)
    - **mode**: Correction mode - base/legal/strict (optional, default: legal)
      - base: LanguageTool only
      - legal: LanguageTool + legal document formatting (quotes, dashes, abbreviations)
      - strict: legal + aggressive normalization
    - **return_edits**: Return list of edits (optional, default: true)

    Returns corrected text with edits and statistics.
    """
    logger.info(
        f"Correction request: mode={request.mode}, "
        f"text_length={len(request.text)}, return_edits={request.return_edits}"
    )

    start_time = time.time()

    try:
        # Run correction engine
        corrected_text, edits = engine.correct(request.text, mode=request.mode)

        processing_time = (time.time() - start_time) * 1000

        # Convert TextEdit to Edit schema
        edits_list = []
        if request.return_edits:
            edits_list = [
                Edit(
                    offset=e.offset,
                    length=e.length,
                    original=e.original,
                    replacement=e.replacement,
                    message=e.message,
                )
                for e in edits
            ]

        stats = Stats(
            chars_count=len(corrected_text),
            edits_count=len(edits),
            processing_time_ms=round(processing_time, 2),
        )

        logger.debug(
            f"Correction complete: chars={stats.chars_count}, "
            f"edits={stats.edits_count}, time={stats.processing_time_ms}ms"
        )

        return CorrectionResponse(result=corrected_text, edits=edits_list, stats=stats)

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
