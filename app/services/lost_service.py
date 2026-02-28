from datetime import datetime
from bson import ObjectId

# from app.database import mongo.items
from app.constants import ITEM_STATUS_ACTIVE, ITEM_STATUS_LOST
from app.connectors import mongo , minio

async def update_lost_mode(item_id: str, payload, user):
    item = mongo.items.find_one({
        "_id": ObjectId(item_id),
        "user_id": user["_id"]
    })

    if not item:
        return True, {
            "status": False,
            "message": "404 | Item not found",
            "data": None
        }

    new_status = ITEM_STATUS_LOST if payload.lost else ITEM_STATUS_ACTIVE

    mongo.items.update_one(
        {"_id": ObjectId(item_id)},
        {
            "$set": {
                "status": new_status,
                "lost_note": payload.note,
                "updated_at": datetime.utcnow()
            }
        }
    )

    return False, {
        "status": True,
        "message": "200 | Lost mode updated",
        "data": {
            "item_id": item_id,
            "status": new_status
        }
    }
