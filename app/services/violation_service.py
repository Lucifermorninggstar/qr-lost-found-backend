from datetime import datetime
from bson import ObjectId

from app.constants import ITEM_STATUS_ACTIVE
from app.connectors import mongo , minio

async def report_violation(token: str, payload):
    item = mongo.items.find_one({"qr_token": token})
    if not item:
        return True, {
            "status": False,
            "message": "404 | Invalid QR token",
            "data": None
        }

    mongo.violations.insert_one({
        "item_id": item["_id"],
        "violation_type": payload.type,
        "message": payload.message,
        "location": {
            "lat": payload.latitude,
            "lng": payload.longitude
        },
        "reported_at": datetime.utcnow()
    })

    return False, {
        "status": True,
        "message": "201 | Violation reported successfully",
        "data": {
            "item_id": str(item["_id"]),
            "type": payload.type
        }
    }
