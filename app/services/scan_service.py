# # app/services/scan_service.py
# from datetime import datetime
# from bson import ObjectId

# from app.connectors import mongo, minio
# from app.constants import ITEM_STATUS_LOST
# from app import main
# import json


# async def scan_qr(token: str, payload=None):

#     # 1. Item
#     item = mongo.items.find_one({"qr_token": token})
#     if not item:
#         return True, {"status": False, "message": "404 | Invalid or expired QR", "data": None}

#     # 2. Owner
#     owner = mongo.users.find_by_id(item["user_id"])
#     if not owner:
#         return True, {"status": False, "message": "404 | Owner not found", "data": None}

#     # 3. Scan log
#     mongo.scan_logs.insert_one({
#         "item_id":    item["_id"],
#         "scanned_at": datetime.utcnow(),
#         "location": {
#             "lat": payload.latitude  if payload else None,
#             "lng": payload.longitude if payload else None,
#         },
#         "message": payload.message if payload else None,
#     })

#     # 4. Notification
#     owner_id = str(item["user_id"])
#     notif = {
#         "user_id":    owner_id,
#         "type":       "SCAN",
#         "message":    f"📦 Your item '{item['name']}' was just scanned",
#         "item_id":    str(item["_id"]),
#         "item_name":  item["name"],
#         "read":       False,
#         "created_at": datetime.utcnow(),
#     }
#     mongo.notifications.insert_one(notif)
#     await main.send_to_user(owner_id, {
#         "type":       "SCAN",
#         "message":    notif["message"],
#         "item_name":  item["name"],
#         "item_id":    str(item["_id"]),
#         "created_at": datetime.utcnow().isoformat(),
#     })

#     # 5. Privacy & contact
#     privacy = item.get("privacy", {})
#     contact = {}
#     if privacy.get("show_email"): contact["email"] = owner.get("email")
#     if privacy.get("show_phone"): contact["phone"] = owner.get("phone")

#     # 6. Item image presigned URL
#     item_image_url = minio.uploads.safe_presigned_get(item.get("image"))

#     # 7. Vehicle details
#     item_type       = item.get("item_type", "other")
#     vehicle_details = item.get("vehicle_details", {})
#     vehicle_public  = item.get("vehicle_public",  {})

#     public_vehicle = None
#     if item_type == "vehicle":
#         public_vehicle = {
#             "type":  vehicle_details.get("type"),
#             "color": vehicle_details.get("color"),
#             "make":  vehicle_details.get("make"),
#             "model": vehicle_details.get("model"),
#             "year":  vehicle_details.get("year"),
#         }
#         if vehicle_public.get("show_vehicle_number", True):
#             public_vehicle["number"] = vehicle_details.get("number")
#         if vehicle_public.get("show_rc", True):
#             public_vehicle["rc_number"] = vehicle_details.get("rc_number")
#         if vehicle_public.get("show_insurance", True):
#             public_vehicle["insurance_expiry"] = vehicle_details.get("insurance_expiry")
#         if vehicle_public.get("show_puc", True):
#             public_vehicle["puc_expiry"] = vehicle_details.get("puc_expiry")

#     # 8. Owner name visibility
#     owner_name = owner.get("name") if vehicle_public.get("show_owner_name", True) else None

#     return False, {
#         "status":  True,
#         "message": "200 | QR scanned successfully",
#         "data": {
#             "item": {
#                 "name":            item["name"],
#                 "description":     item.get("description"),
#                 "status":          item["status"],
#                 "image":           item_image_url,      # ← presigned URL
#                 "item_type":       item_type,
#                 "vehicle_details": public_vehicle,
#                 "vehicle_public":  vehicle_public,
#                 "owner_name":      owner_name,
#             },
#             "contact":   contact,
#             "lost_mode": item["status"] == ITEM_STATUS_LOST,
#         }
#     }

# app/services/scan_service.py
from datetime import datetime
from bson import ObjectId
from app.connectors import mongo, minio
from app.constants import ITEM_STATUS_LOST
from app import main


async def scan_qr(token: str, payload=None):

    item = mongo.items.find_one({"qr_token": token})
    if not item:
        return True, {"status": False, "message": "404 | Invalid or expired QR", "data": None}

    owner = mongo.users.find_by_id(item["user_id"])
    if not owner:
        return True, {"status": False, "message": "404 | Owner not found", "data": None}

    mongo.scan_logs.insert_one({
        "item_id":    item["_id"],
        "scanned_at": datetime.utcnow(),
        "location": {
            "lat": payload.latitude  if payload else None,
            "lng": payload.longitude if payload else None,
        },
        "message": payload.message if payload else None,
    })

    owner_id = str(item["user_id"])
    notif = {
        "user_id":    owner_id,
        "type":       "SCAN",
        "message":    f"📦 Your item '{item['name']}' was just scanned",
        "item_id":    str(item["_id"]),
        "item_name":  item["name"],
        "read":       False,
        "created_at": datetime.utcnow(),
    }
    mongo.notifications.insert_one(notif)
    await main.send_to_user(owner_id, {
        "type":       "SCAN",
        "message":    notif["message"],
        "item_name":  item["name"],
        "item_id":    str(item["_id"]),
        "created_at": datetime.utcnow().isoformat(),
    })

    privacy = item.get("privacy", {})
    contact = {}
    if privacy.get("show_email"): contact["email"] = owner.get("email")
    if privacy.get("show_phone"): contact["phone"] = owner.get("mobile_number")

    item_image_url  = minio.uploads.safe_presigned_get(item.get("image"))
    item_type       = item.get("item_type", "other")
    vehicle_details = item.get("vehicle_details", {})
    vehicle_public  = item.get("vehicle_public",  {})

    public_vehicle      = None
    public_vehicle_docs = {}

    if item_type == "vehicle":
        public_vehicle = {
            "type":  vehicle_details.get("type"),
            "color": vehicle_details.get("color"),
            "make":  vehicle_details.get("make"),
            "model": vehicle_details.get("model"),
            "year":  vehicle_details.get("year"),
        }
        if vehicle_public.get("show_vehicle_number", True):
            public_vehicle["number"] = vehicle_details.get("number")
        if vehicle_public.get("show_rc", True):
            public_vehicle["rc_number"] = vehicle_details.get("rc_number")
        if vehicle_public.get("show_insurance", True):
            public_vehicle["insurance_expiry"] = vehicle_details.get("insurance_expiry")
        if vehicle_public.get("show_puc", True):
            public_vehicle["puc_expiry"] = vehicle_details.get("puc_expiry")

        DOC_LABELS = {
            "rc": "RC / Registration", "insurance": "Insurance",
            "puc": "PUC / Pollution",  "fitness": "Fitness Certificate",
            "permit": "Permit",        "other": "Other",
        }
        doc_visibility = {
            "rc":        vehicle_public.get("show_rc",        True),
            "insurance": vehicle_public.get("show_insurance", True),
            "puc":       vehicle_public.get("show_puc",       True),
            "fitness":   vehicle_public.get("show_fitness",   True),
            "permit":    vehicle_public.get("show_permit",    True),
            "other":     vehicle_public.get("show_other",     True),
        }
        for doc_type, key in item.get("vehicle_docs", {}).items():
            if key and doc_visibility.get(doc_type, True):
                url = minio.documents.safe_presigned_get(key)
                if url:
                    public_vehicle_docs[doc_type] = {
                        "url":   url,
                        "label": DOC_LABELS.get(doc_type, doc_type),
                    }

    owner_name = owner.get("name") if vehicle_public.get("show_owner_name", True) else None

    return False, {
        "status":  True,
        "message": "200 | QR scanned successfully",
        "data": {
            "item": {
                "name":            item["name"],
                "description":     item.get("description"),
                "status":          item["status"],
                "image":           item_image_url,
                "item_type":       item_type,
                "vehicle_details": public_vehicle,
                "vehicle_public":  vehicle_public,
                "vehicle_docs":    public_vehicle_docs,
                "owner_name":      owner_name,
            },
            "contact":   contact,
            "lost_mode": item["status"] == ITEM_STATUS_LOST,
        }
    }