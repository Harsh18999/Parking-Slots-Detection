"""
Reference image management — upload reference images for the embedding DB.
Each uploaded image becomes a unique "type" with an auto-generated ID and color.
Users can upload as many as they want; each forms a classification category.

All reference images are held IN MEMORY only — nothing is written to disk.
"""
import io
import random
import colorsys
import logging
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional, List

from PIL import Image

from services.sagemaker_service import sagemaker_service

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Color generator ───────────────────────────────────────────────────────────

def _generate_color():
    """Generate a vibrant random color as (R, G, B) 0-255 and hex string."""
    hue = random.random()
    r, g, b = colorsys.hsv_to_rgb(hue, 0.75, 0.9)
    rgb = (int(r * 255), int(g * 255), int(b * 255))
    hex_color = "#{:02x}{:02x}{:02x}".format(*rgb)
    return rgb, hex_color


# In-memory registry: { type_id: { name, color_hex, color_rgb, image_bytes, image_pil } }
type_registry: dict = {}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/upload-reference")
async def upload_reference_image(
    file: UploadFile = File(...),
    label: Optional[str] = Form(None, description="Optional human-readable label for this type"),
):
    """
    Upload a single reference image. It becomes a new classification type.
    A unique ID and random color are auto-assigned.
    Optionally provide a label (e.g. 'Handicap Parking').
    Image is kept in memory only — never written to disk.
    """
    if not file.filename or not file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        raise HTTPException(status_code=400, detail="Only PNG/JPG images are accepted.")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image too large (max 10 MB).")

    # Generate unique type ID
    type_id = f"type_{uuid4().hex[:8]}"
    rgb, hex_color = _generate_color()
    display_name = label.strip() if label else file.filename.rsplit(".", 1)[0]

    # Keep PIL Image in memory for embedding generation
    pil_image = Image.open(io.BytesIO(content)).convert("RGB")

    # Register in memory
    type_registry[type_id] = {
        "name": display_name,
        "color_hex": hex_color,
        "color_rgb": rgb,
        "image_bytes": content,
        "image_pil": pil_image,
        "image_count": 1,
    }

    logger.info(f"Reference image uploaded (in-memory): {type_id} ({display_name}) color={hex_color}")

    return {
        "type_id": type_id,
        "name": display_name,
        "color_hex": hex_color,
        "filename": file.filename,
    }


@router.post("/upload-references-batch")
async def upload_references_batch(files: List[UploadFile] = File(...)):
    """
    Upload multiple reference images at once. Each becomes its own type.
    All images are kept in memory only.
    """
    results = []

    for file in files:
        if not file.filename or not file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
            continue

        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            continue

        type_id = f"type_{uuid4().hex[:8]}"
        rgb, hex_color = _generate_color()
        display_name = file.filename.rsplit(".", 1)[0]

        pil_image = Image.open(io.BytesIO(content)).convert("RGB")

        type_registry[type_id] = {
            "name": display_name,
            "color_hex": hex_color,
            "color_rgb": rgb,
            "image_bytes": content,
            "image_pil": pil_image,
            "image_count": 1,
        }

        results.append({
            "type_id": type_id,
            "name": display_name,
            "color_hex": hex_color,
            "filename": file.filename,
        })

    logger.info(f"Batch upload (in-memory): {len(results)} reference images added")
    return {"uploaded": results, "total": len(results)}


@router.delete("/reference/{type_id}")
async def delete_reference(type_id: str):
    """Delete a reference type from memory."""
    if type_id not in type_registry:
        raise HTTPException(status_code=404, detail="Type not found.")

    del type_registry[type_id]

    # Remove from embedding DB if present
    if type_id in sagemaker_service.db:
        del sagemaker_service.db[type_id]

    logger.info(f"Deleted reference type (in-memory): {type_id}")
    return {"message": f"Type '{type_id}' deleted.", "type_id": type_id}


@router.post("/build-embeddings")
async def build_embeddings():
    """
    Build the embedding database from all uploaded reference images (in-memory).
    Calls SageMaker to compute rotation-invariant embeddings for each type.
    """
    if not type_registry:
        raise HTTPException(status_code=400, detail="No reference images uploaded. Upload images first.")

    try:
        # Build embeddings from in-memory PIL images
        for type_id, info in type_registry.items():
            pil_image = info.get("image_pil")
            if pil_image:
                sagemaker_service.build_rotation_invariant_embedding(pil_image, type_id)

        sagemaker_service._initialized = len(sagemaker_service.db) > 0

        if sagemaker_service.is_initialized:
            types = list(sagemaker_service.db.keys())
            return {
                "message": "Embedding database built successfully.",
                "types": types,
                "initialized": True,
            }
        else:
            return {
                "message": "Failed to build embeddings. Check SageMaker endpoint.",
                "types": [],
                "initialized": False,
            }
    except Exception as e:
        logger.error(f"Embedding build failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to build embeddings: {str(e)}")


@router.get("/reference-status")
async def reference_status():
    """Return all registered types with their metadata."""
    types = []
    for type_id, info in type_registry.items():
        types.append({
            "type_id": type_id,
            "name": info["name"],
            "color_hex": info["color_hex"],
            "has_embedding": type_id in sagemaker_service.db,
        })

    return {
        "types": types,
        "total": len(types),
        "embedding_db_initialized": sagemaker_service.is_initialized,
        "embedding_db_types": list(sagemaker_service.db.keys()),
    }
