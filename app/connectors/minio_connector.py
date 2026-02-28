# """
# app/connectors/minio_connector.py
# ===================================
# Class-based MinIO connector with bucket-level accessors.

# Example:
#     from app.connectors import minio

#     # Upload a file
#     key = await minio.uploads.put(file_bytes, "photo.jpg", "image/jpeg")

#     # Get presigned URL (for frontend to display)
#     url = minio.uploads.presigned_get("photo.jpg")

#     # Delete
#     minio.uploads.delete("photo.jpg")

#     # Save FastAPI UploadFile
#     key = await minio.uploads.put_upload_file(upload_file, prefix="items")

#     # Save QR code bytes
#     key = minio.qr_codes.put_bytes(qr_bytes, "token123.png")
# """

# from __future__ import annotations

# import io
# import os
# import uuid
# from datetime import timedelta
# from typing import Optional

# from loguru import logger
# from minio import Minio
# from minio.error import S3Error
# from fastapi import UploadFile


# # ── Bucket Wrapper ────────────────────────────────────────────

# class BucketWrapper:
#     """
#     Wraps MinIO operations for a single bucket.
#     All methods are synchronous (minio-py is sync).
#     """

#     def __init__(self, client: Minio, bucket_name: str, presign_expiry: int = 3600):
#         self._client  = client
#         self._bucket  = bucket_name
#         self._expiry  = presign_expiry

#     @property
#     def bucket_name(self) -> str:
#         return self._bucket

#     # ── Put / Upload ─────────────────────────────────────────
#     def put_bytes(
#         self,
#         data:         bytes,
#         object_name:  str,
#         content_type: str = "application/octet-stream",
#     ) -> str:
#         """
#         Upload raw bytes. Returns object_name (use as key to get later).
#         """
#         try:
#             self._client.put_object(
#                 bucket_name  = self._bucket,
#                 object_name  = object_name,
#                 data         = io.BytesIO(data),
#                 length       = len(data),
#                 content_type = content_type,
#             )
#             logger.debug(f"[minio:{self._bucket}] uploaded {object_name}")
#             return object_name
#         except S3Error as e:
#             logger.error(f"[minio:{self._bucket}] put_bytes error: {e}")
#             raise

#     def put_stream(
#         self,
#         stream,
#         object_name:  str,
#         length:       int,
#         content_type: str = "application/octet-stream",
#     ) -> str:
#         """Upload a file-like stream."""
#         try:
#             self._client.put_object(
#                 bucket_name  = self._bucket,
#                 object_name  = object_name,
#                 data         = stream,
#                 length       = length,
#                 content_type = content_type,
#             )
#             return object_name
#         except S3Error as e:
#             logger.error(f"[minio:{self._bucket}] put_stream error: {e}")
#             raise

#     async def put_upload_file(
#         self,
#         file:   UploadFile,
#         prefix: str = "",
#     ) -> str:
#         """
#         Save a FastAPI UploadFile to MinIO.
#         Generates a UUID filename.
#         Returns the object_name (store in DB as the key).

#         Usage:
#             key = await minio.uploads.put_upload_file(file, prefix="items")
#             # key = "items/uuid4.jpg"
#         """
#         ext          = os.path.splitext(file.filename or "file")[1] or ".bin"
#         unique_name  = f"{uuid.uuid4()}{ext}"
#         object_name  = f"{prefix}/{unique_name}" if prefix else unique_name
#         content_type = file.content_type or "application/octet-stream"

#         data = await file.read()
#         return self.put_bytes(data, object_name, content_type)

#     # ── Get presigned URL ────────────────────────────────────
#     def presigned_get(self, object_name: str, expiry_seconds: int = None) -> str:
#         """
#         Returns a temporary URL valid for `expiry_seconds`.
#         Frontend uses this URL to display images.
#         """
#         expiry = timedelta(seconds=expiry_seconds or self._expiry)
#         try:
#             url = self._client.presigned_get_object(
#                 bucket_name = self._bucket,
#                 object_name = object_name,
#                 expires     = expiry,
#             )
#             return url
#         except S3Error as e:
#             logger.error(f"[minio:{self._bucket}] presigned_get error: {e}")
#             raise

#     def presigned_put(self, object_name: str, expiry_seconds: int = None) -> str:
#         """Returns a presigned PUT URL (for direct browser uploads)."""
#         expiry = timedelta(seconds=expiry_seconds or self._expiry)
#         try:
#             return self._client.presigned_put_object(
#                 bucket_name = self._bucket,
#                 object_name = object_name,
#                 expires     = expiry,
#             )
#         except S3Error as e:
#             logger.error(f"[minio:{self._bucket}] presigned_put error: {e}")
#             raise

#     # ── Download / Read ──────────────────────────────────────
#     def get_bytes(self, object_name: str) -> bytes:
#         try:
#             response = self._client.get_object(self._bucket, object_name)
#             return response.read()
#         except S3Error as e:
#             logger.error(f"[minio:{self._bucket}] get_bytes error: {e}")
#             raise
#         finally:
#             try: response.close(); response.release_conn()
#             except Exception: pass

#     # ── Delete ───────────────────────────────────────────────
#     def delete(self, object_name: str) -> None:
#         try:
#             self._client.remove_object(self._bucket, object_name)
#             logger.debug(f"[minio:{self._bucket}] deleted {object_name}")
#         except S3Error as e:
#             logger.error(f"[minio:{self._bucket}] delete error: {e}")
#             raise

#     # ── Check exists ─────────────────────────────────────────
#     def exists(self, object_name: str) -> bool:
#         try:
#             self._client.stat_object(self._bucket, object_name)
#             return True
#         except S3Error:
#             return False

#     # ── List objects ─────────────────────────────────────────
#     def list_objects(self, prefix: str = "", recursive: bool = True) -> list:
#         try:
#             objects = self._client.list_objects(
#                 self._bucket, prefix=prefix, recursive=recursive
#             )
#             return [obj.object_name for obj in objects]
#         except S3Error as e:
#             logger.error(f"[minio:{self._bucket}] list error: {e}")
#             return []

#     # ── Convenience: safe presign (returns None if not found) ─
#     def safe_presigned_get(self, object_name: Optional[str], expiry_seconds: int = None) -> Optional[str]:
#         if not object_name:
#             return None
#         try:
#             return self.presigned_get(object_name, expiry_seconds)
#         except Exception:
#             return None


# # ── Main Connector ────────────────────────────────────────────

# class MinIOConnector:
#     """
#     Singleton MinIO connector.
#     Access buckets as attributes:  minio.uploads, minio.documents, minio.qr_codes
#     """

#     def __init__(self):
#         self._client:   Optional[Minio]                 = None
#         self._buckets:  dict[str, BucketWrapper]        = {}
#         self._expiry:   int                             = 3600

#     def connect(self):
#         endpoint = os.getenv("MINIO_ENDPOINT",  "localhost:5058")
#         user     = os.getenv("MINIO_USER",      "minioadmin")
#         password = os.getenv("MINIO_PASS",      "minioadmin")
#         secure   = os.getenv("MINIO_SECURE",    "false").lower() == "true"
#         self._expiry = int(os.getenv("MINIO_PRESIGN_EXPIRY", "3600"))

#         try:
#             self._client = Minio(
#                 endpoint   = endpoint,
#                 access_key = user,
#                 secret_key = password,
#                 secure     = secure,
#             )
#             # Test connection
#             self._client.list_buckets()
#             logger.success(f"✅ MinIO connected — {endpoint}")
#             self._register_buckets()
#         except Exception as e:
#             logger.critical(f"❌ MinIO connection failed: {e}")
#             raise

#     def disconnect(self):
#         self._client = None
#         logger.info("MinIO disconnected")

#     def _register_buckets(self):
#         """Register all app buckets. Creates them if they don't exist."""
#         bucket_names = {
#             "uploads":   os.getenv("MINIO_BUCKET_UPLOADS", "uploads"),
#             "documents": os.getenv("MINIO_BUCKET_DOCS",    "documents"),
#             "qr_codes":  os.getenv("MINIO_BUCKET_QR",      "qr-codes"),
#         }
#         for attr, bucket_name in bucket_names.items():
#             self._ensure_bucket(bucket_name)
#             self._buckets[attr] = BucketWrapper(self._client, bucket_name, self._expiry)
#             logger.debug(f"  bucket registered: {attr} → {bucket_name}")

#     def _ensure_bucket(self, bucket_name: str):
#         """Create bucket if it doesn't exist."""
#         try:
#             if not self._client.bucket_exists(bucket_name):
#                 self._client.make_bucket(bucket_name)
#                 logger.info(f"  created bucket: {bucket_name}")
#         except S3Error as e:
#             logger.error(f"  bucket ensure error ({bucket_name}): {e}")
#             raise

#     # ── Attribute access ─────────────────────────────────────
#     @property
#     def uploads(self) -> BucketWrapper:
#         """Item images, profile photos."""
#         return self._buckets["uploads"]

#     @property
#     def documents(self) -> BucketWrapper:
#         """Aadhaar, PAN, Licence, RC, Insurance, PUC."""
#         return self._buckets["documents"]

#     @property
#     def qr_codes(self) -> BucketWrapper:
#         """Generated QR code PNG files."""
#         return self._buckets["qr_codes"]

#     def __getattr__(self, name: str) -> BucketWrapper:
#         if name.startswith("_"):
#             raise AttributeError(name)
#         if name in self._buckets:
#             return self._buckets[name]
#         raise AttributeError(f"Bucket '{name}' not registered. Add it in _register_buckets().")

#     def ping(self) -> bool:
#         try:
#             self._client.list_buckets()
#             return True
#         except Exception:
#             return False



"""
Cloudinary-backed MinIO-compatible connector.
Drop-in replacement for existing MinIOConnector.
"""

from __future__ import annotations

import os
import uuid
from typing import Optional

from loguru import logger
from fastapi import UploadFile

import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.utils import cloudinary_url


# ─────────────────────────────────────────────
# Bucket Wrapper (MinIO Compatible)
# ─────────────────────────────────────────────

class BucketWrapper:
    """
    Cloudinary wrapper that mimics MinIO BucketWrapper interface.
    """

    def __init__(self, folder_name: str):
        self._folder = folder_name

    # ─────────────────────────────
    # Upload raw bytes
    # ─────────────────────────────
    def put_bytes(
        self,
        data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        try:
            public_id = f"{self._folder}/{object_name}"

            cloudinary.uploader.upload(
                data,
                public_id=public_id,
                resource_type="auto",   # 🔥 automatic detection
                overwrite=True,
            )

            logger.debug(f"[cloudinary:{self._folder}] uploaded {object_name}")
            return object_name

        except Exception as e:
            logger.error(f"[cloudinary:{self._folder}] put_bytes error: {e}")
            raise

    # ─────────────────────────────
    # Upload FastAPI UploadFile
    # ─────────────────────────────
    async def put_upload_file(
        self,
        file: UploadFile,
        prefix: str = "",
    ) -> str:

        ext = os.path.splitext(file.filename or "file")[1] or ".bin"
        unique_name = f"{uuid.uuid4()}{ext}"

        object_name = f"{prefix}/{unique_name}" if prefix else unique_name

        data = await file.read()

        return self.put_bytes(data, object_name, file.content_type)

    # ─────────────────────────────
    # Get Public URL
    # ─────────────────────────────
    def presigned_get(self, object_name: str, expiry_seconds: int = None) -> str:
        try:
            public_id = f"{self._folder}/{object_name}"

            resource = cloudinary.api.resource(
                public_id,
                resource_type="image"
            )

            return resource["secure_url"]

        except Exception as e:
            logger.error(f"[cloudinary:{self._folder}] presigned_get error: {e}")
            raise

    # ─────────────────────────────
    # Delete File
    # ─────────────────────────────
    def delete(self, object_name: str) -> None:
        try:
            public_id = f"{self._folder}/{object_name}"

            cloudinary.uploader.destroy(
                public_id,
                resource_type="auto"
            )

            logger.debug(f"[cloudinary:{self._folder}] deleted {object_name}")

        except Exception as e:
            logger.error(f"[cloudinary:{self._folder}] delete error: {e}")
            raise

    # ─────────────────────────────
    # Exists
    # ─────────────────────────────
    def exists(self, object_name: str) -> bool:
        try:
            public_id = f"{self._folder}/{object_name}"

            cloudinary.api.resource(
                public_id,
                resource_type="auto"
            )

            return True
        except Exception:
            return False

    # ─────────────────────────────
    # Safe URL
    # ─────────────────────────────
    def safe_presigned_get(
        self,
        object_name: Optional[str],
        expiry_seconds: int = None
    ) -> Optional[str]:
        if not object_name:
            return None
        try:
            return self.presigned_get(object_name)
        except Exception:
            return None


# ─────────────────────────────────────────────
# Main Connector (Same Interface)
# ─────────────────────────────────────────────

class MinIOConnector:
    """
    Cloudinary-backed connector.
    Same attribute access as original MinIOConnector.
    """

    def __init__(self):
        self._buckets = {}

    # ─────────────────────────────
    # Connect
    # ─────────────────────────────
    def connect(self):

        cloudinary.config(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
            api_key=os.getenv("CLOUDINARY_API_KEY"),
            api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        )

        self._register_buckets()
        logger.success("✅ Cloudinary connected")

    def disconnect(self):
        logger.info("Cloudinary disconnected")

    # ─────────────────────────────
    # Bucket registration
    # ─────────────────────────────
    def _register_buckets(self):

        bucket_names = {
            "uploads": "uploads",
            "documents": "documents",
            "qr_codes": "qr_codes",
        }

        for attr, folder_name in bucket_names.items():
            self._buckets[attr] = BucketWrapper(folder_name)

    # ─────────────────────────────
    # Properties (same as before)
    # ─────────────────────────────
    @property
    def uploads(self) -> BucketWrapper:
        return self._buckets["uploads"]

    @property
    def documents(self) -> BucketWrapper:
        return self._buckets["documents"]

    @property
    def qr_codes(self) -> BucketWrapper:
        return self._buckets["qr_codes"]

    def ping(self) -> bool:
        return True