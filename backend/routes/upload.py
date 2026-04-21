"""
Upload route — accepts a PDF file, converts pages to images,
and returns page preview metadata.
"""
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException

from config import MAX_FILE_SIZE_BYTES
from models.schemas import UploadResponse, PagePreview
from services.pdf_service import (
    generate_pdf_id,
    save_uploaded_pdf,
    convert_pdf_to_images,
    validate_pdf,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload-pdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file, convert each page to a PNG preview,
    and return page metadata including dimensions and preview URLs.
    """
    # ── Validate file type ────────────────────────────────────────────
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted. Please upload a .pdf file.",
        )

    # ── Read file & validate size ─────────────────────────────────────
    content = await file.read()

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE_BYTES // (1024*1024)} MB.",
        )

    if not validate_pdf(content):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file. The file does not appear to be a valid PDF.",
        )

    # ── Process ───────────────────────────────────────────────────────
    try:
        pdf_id = generate_pdf_id()
        save_uploaded_pdf(content, pdf_id)
        pages_info = convert_pdf_to_images(pdf_id)
    except Exception as e:
        logger.error(f"PDF processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to process the PDF. Please try again.",
        )

    # ── Build response ────────────────────────────────────────────────
    pages = [
        PagePreview(
            page_number=p["page_number"],
            width=p["width"],
            height=p["height"],
            preview_url=p["data_url"],
        )
        for p in pages_info
    ]

    return UploadResponse(
        pdf_id=pdf_id,
        total_pages=len(pages),
        pages=pages,
    )
