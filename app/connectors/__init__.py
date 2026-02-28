"""
app/connectors
==============
Centralized database and storage connectors.

Usage:
    from app.connectors import mongo, minio

    # MongoDB
    user = await mongo.users.find_one({"email": "x@y.com"})
    await mongo.items.insert_one({...})

    # MinIO
    url  = await minio.uploads.presigned_get("photo.jpg")
    path = await minio.uploads.put_object(file_bytes, "photo.jpg", "image/jpeg")
"""

from app.connectors.mongo_connector import MongoConnector
from app.connectors.minio_connector  import MinIOConnector

# ── Singleton instances ───────────────────────────────────────
mongo = MongoConnector()
minio = MinIOConnector()

__all__ = ["mongo", "minio"]