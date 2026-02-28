from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from bson import ObjectId
from loguru import logger

from app.utils.auth import get_current_user   # your existing JWT dependency

from app.connectors import mongo, minio 

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"]
)


def _serialize(doc: dict) -> dict:
    doc["id"]         = str(doc.pop("_id"))
    doc["user_id"]    = str(doc.get("user_id", ""))
    doc["item_id"]    = str(doc.get("item_id", ""))
    doc["created_at"] = doc["created_at"].isoformat() if isinstance(doc.get("created_at"), datetime) else doc.get("created_at")
    return doc


# ── GET /notifications — fetch all for current user ──────
@router.get("")
async def get_notifications(current_user=Depends(get_current_user)):
    try:
        user_id = str(current_user["_id"])
        docs = list(
            mongo.notifications
            .find({"user_id": user_id})
            .sort("created_at", -1)
            .limit(50)
        )
        return {
            "status": True,
            "data": [_serialize(d) for d in docs],
            "unread": mongo.notifications.count_documents({"user_id": user_id, "read": False}),
        }
    except Exception as e:
        logger.error(f"get_notifications error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch notifications")


# ── PATCH /notifications/read-all — mark all as read ─────
@router.patch("/read-all")
async def mark_all_read(current_user=Depends(get_current_user)):
    try:
        user_id = str(current_user["_id"])
        mongo.notifications.update_many(
            {"user_id": user_id, "read": False},
            {"$set": {"read": True}}
        )
        return {"status": True, "message": "All notifications marked as read"}
    except Exception as e:
        logger.error(f"mark_all_read error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notifications")


# ── PATCH /notifications/{id}/read — mark one as read ────
@router.patch("/{notification_id}/read")
async def mark_one_read(notification_id: str, current_user=Depends(get_current_user)):
    try:
        mongo.notifications.update_one(
            {"_id": ObjectId(notification_id)},
            {"$set": {"read": True}}
        )
        return {"status": True, "message": "Notification marked as read"}
    except Exception as e:
        logger.error(f"mark_one_read error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notification")


# ── DELETE /notifications — clear all ────────────────────
@router.delete("")
async def clear_all(current_user=Depends(get_current_user)):
    try:
        user_id = str(current_user["_id"])
        mongo.notifications.delete_many({"user_id": user_id})
        return {"status": True, "message": "All notifications cleared"}
    except Exception as e:
        logger.error(f"clear_all error: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear notifications")