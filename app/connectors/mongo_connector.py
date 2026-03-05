"""
app/connectors/mongo_connector.py
==================================
Class-based MongoDB connector with typed collection accessors.

All DB operations are centralised here.
Other modules import collection objects and call methods directly.

Example:
    from app.connectors import mongo

    # Insert
    result = mongo.users.insert_one({...})

    # Find
    user = mongo.users.find_one({"email": "x@y.com"})

    # Update
    mongo.items.update_one({"_id": id}, {"$set": {...}})

    # Delete
    mongo.users.delete_one({"_id": id})
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from bson import ObjectId
from loguru import logger
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.results import (
    InsertOneResult, InsertManyResult,
    UpdateResult, DeleteResult
)


# ── Helpers ──────────────────────────────────────────────────

def _to_id(id_: Any) -> ObjectId:
    """Accept str or ObjectId, always return ObjectId."""
    return ObjectId(id_) if isinstance(id_, str) else id_


def _serialize(doc: Optional[Dict]) -> Optional[Dict]:
    """Convert _id → id (str) for API responses."""
    if doc is None:
        return None
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


# ── Collection Wrapper ────────────────────────────────────────

class CollectionWrapper:
    """
    Wraps a pymongo Collection with convenience methods.
    All methods are synchronous (pymongo is sync).
    """

    def __init__(self, collection: Collection, name: str):
        self._col  = collection
        self._name = name

    # ── Raw access ──────────────────────────────────────────
    @property
    def raw(self) -> Collection:
        """Direct pymongo Collection — use when you need full pymongo API."""
        return self._col

    # ── Single document ─────────────────────────────────────
    def find_one(self, filter_: Dict, projection: Dict = None) -> Optional[Dict]:
        try:
            return self._col.find_one(filter_, projection)
        except Exception as e:
            logger.error(f"[{self._name}] find_one error: {e}")
            raise

    def find_by_id(self, id_: Any) -> Optional[Dict]:
        return self.find_one({"_id": _to_id(id_)})

    def find_by_id_serialized(self, id_: Any) -> Optional[Dict]:
        return _serialize(self.find_by_id(id_))

    # ── Raw cursor — backward compatible with old pymongo .find() calls ──
    def find(self, filter_: Dict = None, projection: Dict = None):
        """
        Returns raw pymongo Cursor.
        Backward compatible: works exactly like collection.find().
        Use find_many() for list results with sorting/pagination.
        """
        return self._col.find(filter_ or {}, projection)

    def sort(self, *args, **kwargs):
        """Proxy sort to raw collection (for chained calls)."""
        return self._col.find().sort(*args, **kwargs)

    # ── Multiple documents ───────────────────────────────────
    def find_many(
        self,
        filter_:    Dict  = None,
        sort:       List  = None,
        skip:       int   = 0,
        limit:      int   = 0,
        projection: Dict  = None,
    ) -> List[Dict]:
        try:
            cursor = self._col.find(filter_ or {}, projection)
            if sort:
                cursor = cursor.sort(sort)
            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)
            return list(cursor)
        except Exception as e:
            logger.error(f"[{self._name}] find_many error: {e}")
            raise

    def find_serialized(self, filter_: Dict = None, **kwargs) -> List[Dict]:
        return [_serialize(d) for d in self.find_many(filter_, **kwargs)]

    def count(self, filter_: Dict = None) -> int:
        return self._col.count_documents(filter_ or {})

    # ── Aliases for full pymongo compatibility ───────────────
    def count_documents(self, filter_: Dict = None, **kwargs) -> int:
        """Alias — same as pymongo collection.count_documents()."""
        return self._col.count_documents(filter_ or {}, **kwargs)

    def estimated_document_count(self, **kwargs) -> int:
        return self._col.estimated_document_count(**kwargs)

    def aggregate(self, pipeline: list, **kwargs):
        """Raw pymongo aggregate — returns cursor."""
        return self._col.aggregate(pipeline, **kwargs)

    def find_one_and_update(self, filter_: Dict, update: Dict, **kwargs):
        return self._col.find_one_and_update(filter_, update, **kwargs)

    def find_one_and_delete(self, filter_: Dict, **kwargs):
        return self._col.find_one_and_delete(filter_, **kwargs)

    def distinct(self, key: str, filter_: Dict = None, **kwargs):
        return self._col.distinct(key, filter_ or {}, **kwargs)

    def bulk_write(self, requests: list, **kwargs):
        return self._col.bulk_write(requests, **kwargs)

    def replace_one(self, filter_: Dict, replacement: Dict, **kwargs):
        return self._col.replace_one(filter_, replacement, **kwargs)

    # ── Insert ───────────────────────────────────────────────
    def insert_one(self, document: Dict) -> InsertOneResult:
        try:
            result = self._col.insert_one(document)
            logger.debug(f"[{self._name}] inserted {result.inserted_id}")
            return result
        except Exception as e:
            logger.error(f"[{self._name}] insert_one error: {e}")
            raise

    def insert_many(self, documents: List[Dict]) -> InsertManyResult:
        try:
            result = self._col.insert_many(documents)
            logger.debug(f"[{self._name}] inserted {len(result.inserted_ids)} docs")
            return result
        except Exception as e:
            logger.error(f"[{self._name}] insert_many error: {e}")
            raise

    # ── Update ───────────────────────────────────────────────
    def update_one(self, filter_: Dict, update: Dict, upsert: bool = False) -> UpdateResult:
        try:
            return self._col.update_one(filter_, update, upsert=upsert)
        except Exception as e:
            logger.error(f"[{self._name}] update_one error: {e}")
            raise

    def update_by_id(self, id_: Any, update: Dict) -> UpdateResult:
        return self.update_one({"_id": _to_id(id_)}, update)

    def set_by_id(self, id_: Any, fields: Dict) -> UpdateResult:
        """Shorthand: mongo.users.set_by_id(id, {"name": "John"})"""
        return self.update_by_id(id_, {"$set": fields})

    def update_many(self, filter_: Dict, update: Dict) -> UpdateResult:
        try:
            return self._col.update_many(filter_, update)
        except Exception as e:
            logger.error(f"[{self._name}] update_many error: {e}")
            raise

    def unset_field(self, id_: Any, field: str) -> UpdateResult:
        """Remove a field from a document by id."""
        return self.update_by_id(id_, {"$unset": {field: ""}})

    # ── Delete ───────────────────────────────────────────────
    def delete_one(self, filter_: Dict) -> DeleteResult:
        try:
            return self._col.delete_one(filter_)
        except Exception as e:
            logger.error(f"[{self._name}] delete_one error: {e}")
            raise

    def delete_by_id(self, id_: Any) -> DeleteResult:
        return self.delete_one({"_id": _to_id(id_)})

    def delete_many(self, filter_: Dict) -> DeleteResult:
        try:
            return self._col.delete_many(filter_)
        except Exception as e:
            logger.error(f"[{self._name}] delete_many error: {e}")
            raise

    # ── Indexes ──────────────────────────────────────────────
    def create_index(self, keys, **kwargs):
        return self._col.create_index(keys, **kwargs)

    def ensure_indexes(self):
        """Called once at startup — override per collection if needed."""
        pass


# ── Main Connector ────────────────────────────────────────────

class MongoConnector:
    """
    Singleton MongoDB connector.
    Access collections as attributes:  mongo.users, mongo.items, etc.
    """

    def __init__(self):
        self._client: Optional[MongoClient] = None
        self._db     = None
        self._collections: Dict[str, CollectionWrapper] = {}

    def connect(self):
        uri  = os.getenv("MONGODB_URI", "mongodb+srv://sachinsisodia60:Sachin%40321!@qr-safe.kgpydrj.mongodb.net/?retryWrites=true&w=majority")
        name = os.getenv("MONGO_DB",    "qrsafe_db")
        try:
            self._client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            self._client.admin.command("ping")
            self._db = self._client[name]
            logger.success(f"✅ MongoDB connected — db: {name}")
            self._register_collections()
            self._ensure_all_indexes()
        except Exception as e:
            logger.critical(f"❌ MongoDB connection failed: {e}")
            raise

    def disconnect(self):
        if self._client:
            self._client.close()
            logger.info("MongoDB disconnected")

    def _register_collections(self):
        """Register all app collections here."""
        _names = [
            "users",
            "items",
            "scan_logs",
            "notifications",
            "violations",
            "lost_reports",
        ]
        for name in _names:
            self._collections[name] = CollectionWrapper(self._db[name], name)

    def _ensure_all_indexes(self):
        """Create indexes on startup."""
        try:
            # users
            self.users.raw.create_index("email",     unique=True)
            self.users.raw.create_index("phone")

            # items
            self.items.raw.create_index("user_id")
            self.items.raw.create_index("qr_token",  unique=True)
            self.items.raw.create_index("item_type")
            self.items.raw.create_index("status")

            # scan_logs
            self.scan_logs.raw.create_index([("item_id", ASCENDING), ("scanned_at", DESCENDING)])

            # notifications
            self.notifications.raw.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
            self.notifications.raw.create_index("read")

            # violations
            self.violations.raw.create_index("item_id")

            logger.success("✅ MongoDB indexes ensured")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")

    def __getattr__(self, name: str) -> CollectionWrapper:
        if name.startswith("_"):
            raise AttributeError(name)
        if name in self._collections:
            return self._collections[name]
        # Auto-create if accessed but not pre-registered
        if self._db is not None:
            self._collections[name] = CollectionWrapper(self._db[name], name)
            return self._collections[name]
        raise AttributeError(f"MongoConnector not connected yet. Call mongo.connect() first.")

    def ping(self) -> bool:
        try:
            self._client.admin.command("ping")
            return True
        except Exception:
            return False