"""
Parking slot detection service.
Adapted from the user's Colab pipeline — graph-based rectangle detection
followed by SageMaker classification. Processes entire pages (no annotation regions).
"""
import base64
import io
import math
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple
from uuid import uuid4

import fitz  # PyMuPDF
from PIL import Image

from config import BATCH_SIZE, ZOOM_LEVEL, MIN_SLOT_SCORE
from services.sagemaker_service import sagemaker_service
from utils.image_utils import (
    polygon_crop_from_image,
    sort_rect,
    draw_slots_on_image,
)

logger = logging.getLogger(__name__)

# ─── Geometry helpers ─────────────────────────────────────────────────────────

MIN_LEN, MAX_LEN = 3, 30


def normalize(p) -> Tuple[float, float]:
    return (round(p[0], 0), round(p[1], 0))


def length(p1, p2) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def order_points(pts):
    cx = sum(p[0] for p in pts) / 4
    cy = sum(p[1] for p in pts) / 4
    return sorted(pts, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))


def is_perpendicular(a, b, c, tol=15) -> bool:
    ab = (b[0] - a[0], b[1] - a[1])
    bc = (c[0] - b[0], c[1] - b[1])
    dot = ab[0] * bc[0] + ab[1] * bc[1]
    return abs(dot) < tol


def get_bbox(rect):
    xs, ys = zip(*rect)
    return min(xs), min(ys), max(xs), max(ys)


def is_inside(inner, outer) -> bool:
    x1_min, y1_min, x1_max, y1_max = inner
    x2_min, y2_min, x2_max, y2_max = outer
    return (
        x1_min >= x2_min
        and y1_min >= y2_min
        and x1_max <= x2_max
        and y1_max <= y2_max
    )


# ─── Graph construction ──────────────────────────────────────────────────────


def build_graph(page) -> dict:
    """
    Extract line segments from PDF vector drawings and build an adjacency graph.
    Nodes are normalized endpoints, edges connect endpoints of each line segment.
    """
    graph = defaultdict(set)

    for d in page.get_drawings():
        for item in d["items"]:
            if item[0] == "l":
                p1 = normalize(item[1])
                p2 = normalize(item[2])
                if MIN_LEN < length(p1, p2) < MAX_LEN:
                    graph[p1].add(p2)
                    graph[p2].add(p1)

            elif item[0] == "qu":
                quad = item[1]
                quad = order_points(quad)
                pts = [normalize(p) for p in quad]
                for i in range(4):
                    p1 = pts[i]
                    p2 = pts[(i + 1) % 4]
                    if MIN_LEN < length(p1, p2) < MAX_LEN:
                        graph[p1].add(p2)
                        graph[p2].add(p1)

            elif item[0] == "re":
                rect = item[1]
                pts = [
                    (rect.x0, rect.y0),
                    (rect.x1, rect.y0),
                    (rect.x1, rect.y1),
                    (rect.x0, rect.y1),
                ]
                pts = [normalize(p) for p in pts]
                for i in range(4):
                    p1 = pts[i]
                    p2 = pts[(i + 1) % 4]
                    if MIN_LEN < length(p1, p2) < MAX_LEN:
                        graph[p1].add(p2)
                        graph[p2].add(p1)

    return graph


def detect_slots(graph: dict) -> set:
    """Find all rectangles in the graph by walking 4-cycles with perpendicularity checks."""
    rectangles = set()

    for A in graph:
        for B in graph[A]:
            for C in graph[B]:
                if C == A:
                    continue
                for D in graph[C]:
                    if D == B or D == A:
                        continue
                    if A in graph[D]:
                        pts = [A, B, C, D]
                        if all(
                            is_perpendicular(pts[i - 1], pts[i], pts[(i + 1) % 4])
                            for i in range(4)
                        ):
                            rect = tuple(sorted(pts))
                            rectangles.add(rect)

    return rectangles


# ─── Filtering ────────────────────────────────────────────────────────────────


def filter_redundant_slots(rectangles: list) -> list:
    """Remove rectangles that are fully contained inside larger ones."""
    bboxes = [get_bbox(r) for r in rectangles]
    areas = [(i, (b[2] - b[0]) * (b[3] - b[1])) for i, b in enumerate(bboxes)]
    areas.sort(key=lambda x: x[1])

    keep = [True] * len(rectangles)

    for idx_i, _ in areas:
        for idx_j, _ in reversed(areas):
            if idx_i == idx_j or not keep[idx_j]:
                continue
            if is_inside(bboxes[idx_i], bboxes[idx_j]):
                keep[idx_i] = False
                break

    return [r for i, r in enumerate(rectangles) if keep[i]]


# ─── Crop helper ──────────────────────────────────────────────────────────────


def _crop_one(args):
    full_img, polygon, zoom = args
    return polygon_crop_from_image(full_img, polygon, zoom)


# ─── Color map ────────────────────────────────────────────────────────────────


def get_type_colors() -> dict:
    """Build color map dynamically from the reference type registry."""
    try:
        from routes.references import type_registry
        colors = {}
        for type_id, info in type_registry.items():
            colors[type_id] = info.get("color_rgb", (128, 128, 128))
        colors["UNKNOWN"] = (128, 128, 128)
        colors["DETECTED"] = (100, 100, 100)
        return colors
    except Exception:
        return {"UNKNOWN": (128, 128, 128), "DETECTED": (100, 100, 100)}


# ─── Full page processing pipeline ───────────────────────────────────────────


def process_full_page(
    pdf_bytes: bytes,
    page_number: int,
    progress_callback=None,
) -> dict:
    """
    Full detection pipeline for a single PDF page (no annotations needed).

    1. Open the PDF from in-memory bytes
    2. Build vector-drawing graph
    3. Detect rectangle slots
    4. Remove redundant (nested) rectangles
    5. Crop each slot from a high-res render
    6. Classify via SageMaker embeddings
    7. Draw overlay and save result image
    8. Return per-slot classification results

    If the SageMaker embedding DB is not initialized, skip classification
    and return detected slots only.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_number]

    # Step 1: Build graph & detect all rectangle slots on the page
    if progress_callback:
        progress_callback("Building line graph…")
    graph = build_graph(page)

    if progress_callback:
        progress_callback("Detecting slots…")
    raw_rects = detect_slots(graph)
    rectangles = [sort_rect(list(r)) for r in raw_rects]
    rectangles = filter_redundant_slots(rectangles)

    logger.info(
        f"Page {page_number}: found {len(raw_rects)} raw → "
        f"{len(rectangles)} after dedup"
    )

    if not rectangles:
        doc.close()
        return {
            "page_number": page_number,
            "total_slots": 0,
            "slots": [],
            "summary": {},
        }

    # Step 2: Render page at high zoom for cropping
    if progress_callback:
        progress_callback("Rendering page at high resolution…")
    zoom = ZOOM_LEVEL
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    full_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # Step 3: Crop slot images in parallel
    if progress_callback:
        progress_callback("Cropping slot images…")
    with ThreadPoolExecutor(max_workers=10) as ex:
        cropped_images = list(
            ex.map(_crop_one, [(full_img, r, zoom) for r in rectangles])
        )

    # Step 4: Classify via SageMaker (if available)
    slot_results = []
    summary = defaultdict(int)
    grouped = defaultdict(list)  # for drawing overlays

    if sagemaker_service.is_initialized:
        if progress_callback:
            progress_callback("Classifying slots…")

        total_batches = (len(cropped_images) + BATCH_SIZE - 1) // BATCH_SIZE

        for batch_idx, batch_start in enumerate(range(0, len(cropped_images), BATCH_SIZE)):
            batch = cropped_images[batch_start : batch_start + BATCH_SIZE]

            if progress_callback:
                progress_callback(
                    f"Classifying batch {batch_idx + 1}/{total_batches}…"
                )

            try:
                embeddings = sagemaker_service.call_batch_endpoint(batch)
                classifications = sagemaker_service.classify_embeddings(embeddings)

                for j, (typ, score) in enumerate(classifications):
                    idx = batch_start + j
                    slot_bbox = list(get_bbox(rectangles[idx]))

                    if score >= MIN_SLOT_SCORE:
                        summary[typ] += 1
                        grouped[typ].append(rectangles[idx])
                        slot_results.append({
                            "slot_id": f"slot_{uuid4().hex[:8]}",
                            "parking_type": typ,
                            "confidence": round(score, 4),
                            "bbox": slot_bbox,
                            "points": [list(p) for p in rectangles[idx]],
                        })
                    else:
                        slot_results.append({
                            "slot_id": f"slot_{uuid4().hex[:8]}",
                            "parking_type": "UNKNOWN",
                            "confidence": round(score, 4),
                            "bbox": slot_bbox,
                            "points": [list(p) for p in rectangles[idx]],
                        })

            except Exception as e:
                logger.error(f"SageMaker batch error: {e}")
                for j in range(len(batch)):
                    idx = batch_start + j
                    slot_bbox = list(get_bbox(rectangles[idx]))
                    grouped["DETECTED"].append(rectangles[idx])
                    slot_results.append({
                        "slot_id": f"slot_{uuid4().hex[:8]}",
                        "parking_type": "DETECTED",
                        "confidence": 0.0,
                        "bbox": slot_bbox,
                        "points": [list(p) for p in rectangles[idx]],
                    })
    else:
        # No SageMaker — return detected geometry only
        for idx, slot in enumerate(rectangles):
            slot_bbox = list(get_bbox(slot))
            grouped["DETECTED"].append(slot)
            slot_results.append({
                "slot_id": f"slot_{uuid4().hex[:8]}",
                "parking_type": "DETECTED",
                "confidence": 0.0,
                "bbox": slot_bbox,
                "points": [list(p) for p in slot],
            })

    # Step 5: Draw colored overlays on the page (like the Colab code)
    if progress_callback:
        progress_callback("Generating result image…")

    colors = get_type_colors()

    # Draw on the fitz page using shapes (matching Colab approach)
    for typ in grouped:
        shape = page.new_shape()
        rgb = colors.get(typ, (128, 128, 128))
        # Convert 0-255 RGB to 0-1 for fitz
        fitz_color = (rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)

        for rect_pts in grouped[typ]:
            shape.draw_polyline(list(rect_pts) + [rect_pts[0]])

        shape.finish(color=fitz_color, width=0.5)
        shape.commit()

    # Render the annotated page at preview zoom
    preview_mat = fitz.Matrix(2, 2)
    preview_pix = page.get_pixmap(matrix=preview_mat, alpha=False)

    # Encode result image as base64 data URL (no disk write)
    preview_img = Image.frombytes("RGB", [preview_pix.width, preview_pix.height], preview_pix.samples)
    buf = io.BytesIO()
    preview_img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    result_image_data_url = f"data:image/png;base64,{b64}"

    doc.close()

    return {
        "page_number": page_number,
        "total_slots": len(slot_results),
        "slots": slot_results,
        "summary": dict(summary),
        "result_image_data_url": result_image_data_url,
    }
