"""
Processing route — runs full-page detection in the background
and exposes progress / result endpoints.
"""
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

from models.schemas import (
    ProcessDocumentRequest,
    ProcessPageRequest,
    ProgressResponse,
    ProcessResult,
    PageResult,
    SlotResult,
    TaskStatus,
)
from models.task_store import task_store
from services.pdf_service import get_pdf_bytes, get_pdf_page_count
from services.detection_service import process_full_page

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Background task runners ─────────────────────────────────────────────────


def _run_document_processing(task_id: str, pdf_bytes: bytes, pdf_id: str, total_pages: int):
    """
    Background function that processes ALL pages of a PDF sequentially,
    updating progress in the task store.
    """
    all_page_results = []

    try:
        for page_idx in range(total_pages):
            base_pct = (page_idx / total_pages) * 100

            def progress_cb(msg: str, _base=base_pct, _total=total_pages):
                # Each page gets an equal share of the progress bar
                step_pct = _base + (50 / _total)
                task_store.update_progress(
                    task_id,
                    step_pct,
                    f"Page {page_idx + 1}/{_total}: {msg}",
                    status=TaskStatus.PROCESSING,
                )

            task_store.update_progress(
                task_id,
                base_pct,
                f"Processing page {page_idx + 1}/{total_pages}…",
                status=TaskStatus.PROCESSING,
            )

            result = process_full_page(
                pdf_bytes=pdf_bytes,
                page_number=page_idx,
                progress_callback=progress_cb,
            )

            # Convert to response model
            slot_results = [
                SlotResult(
                    slot_id=s["slot_id"],
                    parking_type=s["parking_type"],
                    confidence=s["confidence"],
                    bbox=s["bbox"],
                )
                for s in result["slots"]
            ]

            result_image_url = result.get("result_image_data_url")

            all_page_results.append(
                PageResult(
                    page_number=result["page_number"],
                    total_slots=result["total_slots"],
                    slots=slot_results,
                    result_image_url=result_image_url,
                    summary=result.get("summary", {}),
                )
            )

        # Build final result
        final = ProcessResult(
            pdf_id=pdf_id,
            pages=all_page_results,
        )

        task_store.set_result(task_id, final.model_dump())
        logger.info(f"Task {task_id} completed: {total_pages} pages processed")

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}", exc_info=True)
        task_store.set_failed(task_id, str(e))


def _run_page_processing(task_id: str, pdf_bytes: bytes, pdf_id: str, page_number: int):
    """
    Background function that processes a SINGLE page of a PDF.
    """
    try:
        def progress_cb(msg: str):
            task_store.update_progress(
                task_id,
                50,  # single page → halfway during processing
                f"Page {page_number + 1}: {msg}",
                status=TaskStatus.PROCESSING,
            )

        task_store.update_progress(
            task_id, 0,
            f"Starting page {page_number + 1}…",
            status=TaskStatus.PROCESSING,
        )

        result = process_full_page(
            pdf_bytes=pdf_bytes,
            page_number=page_number,
            progress_callback=progress_cb,
        )

        slot_results = [
            SlotResult(
                slot_id=s["slot_id"],
                parking_type=s["parking_type"],
                confidence=s["confidence"],
                bbox=s["bbox"],
            )
            for s in result["slots"]
        ]

        result_image_url = result.get("result_image_data_url")

        page_result = PageResult(
            page_number=result["page_number"],
            total_slots=result["total_slots"],
            slots=slot_results,
            result_image_url=result_image_url,
            summary=result.get("summary", {}),
        )

        final = ProcessResult(
            pdf_id=pdf_id,
            pages=[page_result],
        )

        task_store.set_result(task_id, final.model_dump())
        logger.info(f"Task {task_id} completed: page {page_number} processed")

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}", exc_info=True)
        task_store.set_failed(task_id, str(e))


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/process-document")
async def process_document(req: ProcessDocumentRequest, background_tasks: BackgroundTasks):
    """
    Process all pages of a PDF for parking slot detection.
    Returns a task_id to poll for progress.
    """
    pdf_bytes = get_pdf_bytes(req.pdf_id)
    if pdf_bytes is None:
        raise HTTPException(
            status_code=404,
            detail=f"PDF '{req.pdf_id}' not found. Please upload the PDF first.",
        )

    total_pages = get_pdf_page_count(req.pdf_id)

    task_id = str(uuid.uuid4())[:12]
    task_store.create_task(task_id)

    background_tasks.add_task(
        _run_document_processing, task_id, pdf_bytes, req.pdf_id, total_pages
    )

    return {"task_id": task_id, "status": "pending", "total_pages": total_pages}


@router.post("/process-page")
async def process_page(req: ProcessPageRequest, background_tasks: BackgroundTasks):
    """
    Process a specific page of a PDF for parking slot detection.
    Returns a task_id to poll for progress.
    """
    pdf_bytes = get_pdf_bytes(req.pdf_id)
    if pdf_bytes is None:
        raise HTTPException(
            status_code=404,
            detail=f"PDF '{req.pdf_id}' not found. Please upload the PDF first.",
        )

    total_pages = get_pdf_page_count(req.pdf_id)
    if req.page_number >= total_pages:
        raise HTTPException(
            status_code=400,
            detail=f"Page {req.page_number} does not exist. PDF has {total_pages} pages (0-indexed).",
        )

    task_id = str(uuid.uuid4())[:12]
    task_store.create_task(task_id)

    background_tasks.add_task(
        _run_page_processing, task_id, pdf_bytes, req.pdf_id, req.page_number
    )

    return {"task_id": task_id, "status": "pending", "page_number": req.page_number}


@router.get("/progress/{task_id}", response_model=ProgressResponse)
async def get_progress(task_id: str):
    """Poll processing progress for a given task."""
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    result = None
    if task.result:
        result = ProcessResult(**task.result)

    return ProgressResponse(
        task_id=task.task_id,
        status=task.status,
        progress=task.progress,
        message=task.message,
        result=result,
    )


@router.get("/result/{task_id}")
async def get_result(task_id: str):
    """Get the final processing result for a completed task."""
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Task is not yet complete. Current status: {task.status.value}",
        )

    return task.result
