"""
Image processing utilities for cropping, encoding, and drawing overlays.
"""
import base64
import io
import math
import random
from typing import List, Tuple

from PIL import Image, ImageDraw


def encode_image_base64(img: Image.Image, fmt: str = "JPEG") -> str:
    """Encode a PIL image to a base64 string."""
    buffered = io.BytesIO()
    img.save(buffered, format=fmt)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def expand_polygon(poly: List[Tuple[float, float]], scale_long=1.7, scale_short=1.2):
    """
    Expand a polygon outward from its centroid.
    The longer axis gets more expansion for better context capture.
    """
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]

    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)

    width = x1 - x0
    height = y1 - y0

    if width >= height:
        sx, sy = scale_long, scale_short
    else:
        sx, sy = scale_short, scale_long

    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2

    expanded = []
    for x, y in poly:
        nx = cx + (x - cx) * sx
        ny = cy + (y - cy) * sy
        expanded.append((nx, ny))

    return expanded


def polygon_crop_from_image(
    full_img: Image.Image,
    polygon: List[Tuple[float, float]],
    zoom: float,
) -> Image.Image:
    """Crop a polygon region from a full page image with masking."""
    pts = expand_polygon(polygon)

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]

    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)

    bbox_scaled = (
        int(x0 * zoom),
        int(y0 * zoom),
        int(x1 * zoom),
        int(y1 * zoom),
    )

    img = full_img.crop(bbox_scaled)

    shifted = [
        ((x - x0) * zoom, (y - y0) * zoom)
        for x, y in pts
    ]

    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(shifted, fill=255)

    result = Image.new("RGB", img.size, (255, 255, 255))
    result.paste(img, (0, 0), mask)

    return result


def crop_bbox_from_image(
    full_img: Image.Image,
    bbox: Tuple[float, float, float, float],
    zoom: float,
) -> Image.Image:
    """Crop a rectangular bounding box from a full page image."""
    x0, y0, x1, y1 = bbox
    scaled = (
        int(x0 * zoom),
        int(y0 * zoom),
        int(x1 * zoom),
        int(y1 * zoom),
    )
    return full_img.crop(scaled)


def random_color() -> Tuple[int, int, int]:
    """Generate a vibrant random color for annotation display."""
    hue = random.random()
    # HSV → RGB with full saturation and brightness
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(hue, 0.8, 0.9)
    return (int(r * 255), int(g * 255), int(b * 255))


def draw_slots_on_image(
    page_img: Image.Image,
    slots: List[dict],
    colors: dict,
) -> Image.Image:
    """
    Draw detected slot rectangles overlaid on the page image.
    Each slot dict should have 'points' and 'parking_type'.
    """
    result = page_img.copy()
    draw = ImageDraw.Draw(result, "RGBA")

    for slot in slots:
        pts = slot.get("points", [])
        typ = slot.get("parking_type", "UNKNOWN")

        base = colors.get(typ, (128, 128, 128))
        fill = (*base, 50)   # semi-transparent fill
        outline = (*base, 200)

        if len(pts) >= 3:
            flat = [(p[0], p[1]) for p in pts]
            draw.polygon(flat, fill=fill, outline=outline)

    return result


def get_bbox_from_points(points: List[List[float]]) -> Tuple[float, float, float, float]:
    """Get axis-aligned bounding box from a list of points."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))


def sort_rect(points):
    """Sort rectangle points in clockwise order around centroid."""
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    return sorted(points, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
