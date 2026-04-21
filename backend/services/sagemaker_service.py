"""
SageMaker client wrapper for calling embedding inference endpoints.
"""
import base64
import io
import json
import logging
from typing import List, Optional

import boto3
import numpy as np
from PIL import Image

from config import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_REGION,
    SAGEMAKER_ENDPOINT_BATCH,
    SAGEMAKER_ENDPOINT_SINGLE,
)

logger = logging.getLogger(__name__)


class SageMakerService:
    """
    Manages the boto3 SageMaker Runtime client and endpoint calls.
    Also holds the reference embedding database for classification.
    """

    def __init__(self):
        self.client = boto3.client(
            "sagemaker-runtime",
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
        # Reference embedding database: {type_name: {angle: embedding_vector}}
        self.db: dict[str, dict[int, np.ndarray]] = {}
        self._initialized = False

    # ── Endpoint calls ────────────────────────────────────────────────────

    def _encode_image(self, img: Image.Image) -> str:
        """Encode a PIL image to base64 JPEG string for the endpoint payload."""
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    def call_batch_endpoint(self, images: List[Image.Image]) -> List[np.ndarray]:
        """
        Send a batch of images to the embedding endpoint.
        Returns a list of embedding vectors (one per image).
        """
        payload = json.dumps([self._encode_image(img) for img in images])

        response = self.client.invoke_endpoint(
            EndpointName=SAGEMAKER_ENDPOINT_BATCH,
            ContentType="application/json",
            Body=payload,
        )

        result = json.loads(response["Body"].read().decode())
        return [np.array(emb) for emb in result]

    def call_single_endpoint(self, image_bytes: bytes) -> dict:
        """Call the single-image endpoint (for direct inference)."""
        response = self.client.invoke_endpoint(
            EndpointName=SAGEMAKER_ENDPOINT_SINGLE,
            ContentType="application/x-image",
            Body=image_bytes,
        )
        return json.loads(response["Body"].read().decode("utf-8"))

    # ── Embedding database ────────────────────────────────────────────────

    def build_rotation_invariant_embedding(
        self, image: Image.Image, type_name: str
    ):
        """
        Build rotation-invariant reference embeddings for a parking type.
        Rotates the image at multiple angles and stores embeddings.
        Uses PIL.Image.rotate instead of torchvision.
        """
        angles = [0, 45, 90, 135, 180, 225, 270]
        self.db[type_name] = {}

        rotated_images = []
        for angle in angles:
            rotated = image.rotate(-angle, expand=True, fillcolor=(255, 255, 255))
            rotated_images.append(rotated)

        embeddings = self.call_batch_endpoint(rotated_images)

        for angle, emb in zip(angles, embeddings):
            emb = emb / np.linalg.norm(emb)  # L2 normalize
            self.db[type_name][angle] = emb

        logger.info(f"Built embedding DB for type '{type_name}' with {len(angles)} angles")

    def load_reference_images(self, reference_dir: str) -> bool:
        """
        Load reference images from a directory structure:
        reference_images/
          NORMAL/image.png
          STANDARD/image.png
          LIGHT/image.png
        """
        import os

        if not os.path.exists(reference_dir):
            logger.warning(f"Reference directory not found: {reference_dir}")
            return False

        for type_name in os.listdir(reference_dir):
            type_dir = os.path.join(reference_dir, type_name)
            if not os.path.isdir(type_dir):
                continue

            # Take the first image in the directory
            for fname in os.listdir(type_dir):
                if fname.lower().endswith((".png", ".jpg", ".jpeg")):
                    img_path = os.path.join(type_dir, fname)
                    img = Image.open(img_path).convert("RGB")
                    try:
                        self.build_rotation_invariant_embedding(img, type_name)
                    except Exception as e:
                        logger.error(f"Failed to build embedding for {type_name}: {e}")
                    break

        self._initialized = len(self.db) > 0
        return self._initialized

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    # ── Classification ────────────────────────────────────────────────────

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def classify_embeddings(
        self, embeddings: List[np.ndarray]
    ) -> List[tuple]:
        """
        Classify a list of embeddings against the reference database.
        Returns list of (type_name, confidence_score) tuples.
        """
        results = []

        for feat in embeddings:
            feat = np.array(feat)
            best_type = "UNKNOWN"
            best_score = -1.0

            for typ in self.db:
                total_sim = 0.0
                for angle in self.db[typ]:
                    db_emb = self.db[typ][angle]
                    total_sim += self.cosine_similarity(feat, db_emb)
                avg_sim = total_sim / len(self.db[typ])

                if avg_sim > best_score:
                    best_score = avg_sim
                    best_type = typ

            results.append((best_type, best_score))

        return results


# Global singleton
sagemaker_service = SageMakerService()
