from bson import ObjectId
from app.database import items_collection, scan_logs_collection, violation_logs_collection
from app.connectors import mongo, minio

async def get_dashboard_stats(user_id: str):

    # 1️⃣ Get user items
    user_items = list(
        mongo.items.find({"user_id": user_id}, {"_id": 1, "status": 1})
    )

    item_ids = [item["_id"] for item in user_items]

    total_items = len(user_items)

    lost_items = len(
        [item for item in user_items if item.get("status") == "LOST"]
    )

    # 2️⃣ Count scans for those items
    total_scans = mongo.scan_logs.count_documents({
        "item_id": {"$in": item_ids}
    })

    # 3️⃣ Count violations for those items
    total_violations = mongo.violations.count_documents({
        "item_id": {"$in": item_ids}
    })

    return False, {
        "status": True,
        "status_code": 200,
        "message": "Dashboard stats fetched",
        "data": {
            "total_items": total_items,
            "lost_items": lost_items,
            "active_items": total_items - lost_items,
            "total_scans": total_scans,
            "total_violations": total_violations
        }
    }


async def get_item_wise_scan_stats(user_id: str):

    # 1️⃣ Get all user items
    user_items = list(
        mongo.items.find(
            {"user_id": user_id},
            {"_id": 1, "name": 1, "status": 1}
        )
    )

    if not user_items:
        return False, {
            "status": True,
            "status_code": 200,
            "message": "No items found",
            "data": []
        }

    item_ids = [item["_id"] for item in user_items]

    # 2️⃣ Aggregation on scan_logs
    pipeline = [
        {
            "$match": {
                "item_id": {"$in": item_ids}
            }
        },
        {
            "$sort": {"scanned_at": -1}
        },
        {
            "$group": {
                "_id": "$item_id",
                "total_scans": {"$sum": 1},
                "last_scanned_at": {"$first": "$scanned_at"},
                "last_location": {"$first": "$location"},
                "last_message": {"$first": "$message"}
            }
        }
    ]

    scan_stats = list(mongo.scan_logs.aggregate(pipeline))

    # Convert to dictionary for fast lookup
    scan_map = {stat["_id"]: stat for stat in scan_stats}

    # 3️⃣ Merge with item data
    response = []

    for item in user_items:
        stat = scan_map.get(item["_id"])

        response.append({
            "item_id": str(item["_id"]),
            "name": item.get("name"),
            "status": item.get("status"),
            "total_scans": stat["total_scans"] if stat else 0,
            "last_scanned_at": stat["last_scanned_at"] if stat else None,
            "last_location": stat["last_location"] if stat else None,
            "last_message": stat["last_message"] if stat else None
        })

    return False, {
        "status": True,
        "status_code": 200,
        "message": "Item wise scan stats fetched",
        "data": response
    }