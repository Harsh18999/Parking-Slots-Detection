"""
PDF handling service — upload, convert to images, retrieve pages.
All data is held in memory — nothing is written to disk.
"""
import io
import uuid
import base64
from typing import Dict, List, Optional

import fitz  # PyMuPDF
from PIL import Image

from config import PREVIEW_ZOOM

# ── In-memory store ───────────────────────────────────────────────────────────
# Keyed by pdf_id → {pdf_bytes, pages: [{page_number, width, height, data_url}]}
_pdf_store: Dict[str, dict] = {}


def generate_pdf_id() -> str:
    """Generate a unique identifier for an uploaded PDF."""
    return str(uuid.uuid4())[:12]


def save_uploaded_pdf(pdf_bytes: bytes, pdf_id: str) -> None:
    """Store an uploaded PDF's raw bytes in memory."""
    _pdf_store.clear()
    _pdf_store[pdf_id] = {
        "pdf_bytes": pdf_bytes,
        "pages": [],
    }


def convert_pdf_to_images(
    pdf_id: str,
    zoom: float = PREVIEW_ZOOM,
) -> List[dict]:
    """
    Convert all pages of an in-memory PDF to PNG images (as base64 data URLs).
    Returns a list of page info dicts: {page_number, width, height, data_url}.
    """
    entry = _pdf_store.get(pdf_id)
    if entry is None:
        raise ValueError(f"PDF '{pdf_id}' not found in memory store.")

    doc = fitz.open(stream=entry["pdf_bytes"], filetype="pdf")
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Encode as base64 data URL
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        data_url = f"data:image/png;base64,{b64}"

        pages.append({
            "page_number": page_num,
            "width": pix.width,
            "height": pix.height,
            "data_url": data_url,
        })

    doc.close()
    entry["pages"] = pages
    return pages


def get_page_image_data_url(pdf_id: str, page_number: int) -> Optional[str]:
    """Return the base64 data URL for a rendered page image."""
    entry = _pdf_store.get(pdf_id)
    if entry is None:
        return None
    for p in entry["pages"]:
        if p["page_number"] == page_number:
            return p["data_url"]
    return None


def get_pdf_bytes(pdf_id: str) -> Optional[bytes]:
    """Return the raw PDF bytes held in memory."""
    entry = _pdf_store.get(pdf_id)
    if entry is None:
        return None
    return entry["pdf_bytes"]


def get_pdf_page_count(pdf_id: str) -> int:
    """Return the number of pages in a stored PDF."""
    entry = _pdf_store.get(pdf_id)
    if entry is None:
        raise ValueError(f"PDF '{pdf_id}' not found in memory store.")
    doc = fitz.open(stream=entry["pdf_bytes"], filetype="pdf")
    count = len(doc)
    doc.close()
    return count


def validate_pdf(file_bytes: bytes) -> bool:
    """Check that the bytes represent a valid PDF (magic bytes)."""
    return file_bytes[:5] == b"%PDF-"


def remove_pdf(pdf_id: str) -> None:
    """Remove a PDF and its rendered pages from the in-memory store."""
    _pdf_store.pop(pdf_id, None)
