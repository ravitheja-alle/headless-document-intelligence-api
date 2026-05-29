import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.api import routes

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""AI-powered document intelligence platform for PDF ingestion,OCR, semantic search, structured extraction, and RAG."""
)

app.include_router(routes.router)

# 1. Handle explicit validation errors from our services
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.warning(f"Validation Error: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid Input", "detail": str(exc)},
    )

# 2. Handle upstream exhaustion (Tenacity gives up)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Server Error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": "An unexpected system failure occurred."},
    )
@app.get("/")
async def root():
    return {
        "project": "DocQuery AI",
        "description": "AI-powered document intelligence platform",
        "docs": "/docs",
        "health": "/health"
    }
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME}