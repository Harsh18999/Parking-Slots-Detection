"""
Application configuration loaded from environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# AWS / SageMaker
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
SAGEMAKER_ENDPOINT_SINGLE = os.getenv("SAGEMAKER_ENDPOINT_SINGLE")
SAGEMAKER_ENDPOINT_BATCH = os.getenv("SAGEMAKER_ENDPOINT_BATCH")

# File handling
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

# Processing
BATCH_SIZE = 15
ZOOM_LEVEL = 5          # high-res rendering for cropping
PREVIEW_ZOOM = 2        # lower-res for page previews
MIN_SLOT_SCORE = 0.65   # minimum cosine similarity for classification
