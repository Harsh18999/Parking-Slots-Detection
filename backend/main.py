"""
FastAPI application entry point.
Registers routes, CORS, static file serving, and startup events.
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.upload import router as upload_router
from routes.process import router as process_router
from routes.references import router as references_router

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    On startup:
      - PDFs and page images are held in memory — no disk directories needed.
    """
    logger.info("Application started. All PDF data is in-memory only.")

    yield  # app is running

    logger.info("Shutting down…")


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Parking Slot Detection API",
    description="Upload PDFs, annotate regions, and detect parking slots.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NOTE: Static file serving removed — page previews are returned as base64 data URLs
# NOTE: /static-output removed — result images are now returned as base64 data URLs

# ── Routes ─────────────────────────────────────────────────────────────────────
app.include_router(upload_router, tags=["Upload"])
app.include_router(process_router, tags=["Processing"])
app.include_router(references_router, tags=["References"])


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    from services.sagemaker_service import sagemaker_service
    return {
        "status": "ok",
        "sagemaker_initialized": sagemaker_service.is_initialized,
    }
