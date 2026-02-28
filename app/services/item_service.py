# import uuid
# import qrcode
# import shutil
# from pathlib import Path
# from bson import ObjectId
# import json

# from app.constants import ITEM_STATUS_ACTIVE, ITEM_STATUS_LOST
# from app.connectors import mongo, minio

# QR_DIR = Path("qr_codes")
# QR_DIR.mkdir(exist_ok=True)

# UPLOAD_DIR = Path("uploads")
# UPLOAD_DIR.mkdir(exist_ok=True)


# async def create_item(payload, image, user, item_type, vehicle_details, vehicle_public):

#     qr_token = str(uuid.uuid4())

#     image_path = None

#     # Save image if provided
#     if image:
#         image_filename = f"{uuid.uuid4()}_{image.filename}"
#         file_location = UPLOAD_DIR / image_filename

#         with open(file_location, "wb") as buffer:
#             shutil.copyfileobj(image.file, buffer)

#         image_path = str(file_location)

#     vd = json.loads(vehicle_details) if vehicle_details else {}
#     vp = json.loads(vehicle_public)  if vehicle_public  else {}

#     item_doc = {
#         "user_id": user["_id"],
#         "name": payload.name,
#         "description": payload.description,
#         "qr_token": qr_token,
#         "status": ITEM_STATUS_ACTIVE,
#         "image": image_path,
#         "privacy": {
#             "show_phone": payload.show_phone,
#             "show_email": payload.show_email
#         },
#         "item_type": item_type,
#         "vehicle_details": vd,
#         "vehicle_public":  vp,
#     }

#     result = mongo.items.insert_one(item_doc)

#     # Generate QR
#     qr_url = f"http://localhost:8000/q/{qr_token}"
#     img = qrcode.make(qr_url)

#     qr_path = QR_DIR / f"{qr_token}.png"
#     img.save(qr_path)

#     return False, {
#         "status": True,
#         "message": "201 | Item created successfully",
#         "data": {
#             "item_id": str(result.inserted_id),
#             "qr_token": qr_token,
#             "qr_image": f"/qr_codes/{qr_token}.png",
#             "image": image_path
#         }
#     }

# async def get_my_items(user, page: int = 1, limit: int = 6):

#     skip = (page - 1) * limit

#     cursor = mongo.items.find(
#         {"user_id": user["_id"]}
#     ).skip(skip).limit(limit)

#     total = mongo.items.count_documents(
#         {"user_id": user["_id"]}
#     )

#     items = []

#     for doc in cursor:
#         items.append({
#             "id": str(doc["_id"]),
#             "name": doc["name"],
#             "qr_token": doc["qr_token"],
#             "status": doc["status"],
#             "image": doc.get("image")
#         })

#     return False, {
#         "status": True,
#         "message": "200 | Items fetched successfully",
#         "data": {
#             "items": items,
#             "total": total,
#             "page": page,
#             "limit": limit
#         }
#     }

# async def delete_item(item_id: str, user):

#     doc = mongo.items.find_one({
#         "_id": ObjectId(item_id),
#         "user_id": user["_id"]
#     })

#     if not doc:
#         return True, {
#             "status": False,
#             "message": "404 | Item not found",
#             "data": None
#         }

#     mongo.items.delete_one({
#         "_id": ObjectId(item_id)
#     })

#     return False, {
#         "status": True,
#         "message": "200 | Item deleted",
#         "data": None
#     }

# async def update_item(item_id: str, payload, user):

#     doc = mongo.items.find_one({
#         "_id": ObjectId(item_id),
#         "user_id": user["_id"]
#     })

#     if not doc:
#         return True, {
#             "status": False,
#             "message": "404 | Item not found",
#             "data": None
#         }

#     mongo.items.update_one(
#         {"_id": ObjectId(item_id)},
#         {"$set": {
#             "name": payload.name,
#             "description": payload.description
#         }}
#     )

#     return False, {
#         "status": True,
#         "message": "200 | Item updated",
#         "data": None
#     }


# async def toggle_status(item_id, user):

#     item = mongo.items.find_one({
#         "_id": ObjectId(item_id),
#         "user_id": user["_id"]
#     })

#     if not item:
#         return True, {
#             "status": False,
#             "message": "404 | Item not found",
#             "data": None
#         }

#     new_status = (
#         ITEM_STATUS_LOST
#         if item["status"] == ITEM_STATUS_ACTIVE
#         else ITEM_STATUS_ACTIVE
#     )

#     mongo.items.update_one(
#         {"_id": ObjectId(item_id)},
#         {"$set": {"status": new_status}}
#     )

#     return False, {
#         "status": True,
#         "message": "200 | Status updated",
#         "data": {"new_status": new_status}
#     }


# app/services/item_service.py
import uuid
import qrcode
import io
from bson import ObjectId
import json
from typing import Optional
from fastapi import UploadFile, File, Form


from app.constants import ITEM_STATUS_ACTIVE, ITEM_STATUS_LOST
from app.connectors import mongo, minio

from loguru import logger 

async def create_item(payload, image, user, item_type, vehicle_details, vehicle_public):
    qr_token   = str(uuid.uuid4())
    image_key  = None

    # ── Upload item image to MinIO ────────────────────────────
    if image and image.filename:
        try:
            image_key = await minio.uploads.put_upload_file(image, prefix="items")
        except Exception as e:
            # Non-fatal — item still gets created without image
            from loguru import logger
            logger.warning(f"Item image upload failed: {e}")

    vd = json.loads(vehicle_details) if vehicle_details else {}
    vp = json.loads(vehicle_public)  if vehicle_public  else {}

    item_doc = {
        "user_id":         user["_id"],
        "name":            payload.name,
        "description":     payload.description,
        "qr_token":        qr_token,
        "status":          ITEM_STATUS_ACTIVE,
        "image":           image_key,          # MinIO object key (not a path)
        "privacy": {
            "show_phone": payload.show_phone,
            "show_email": payload.show_email,
        },
        "item_type":       item_type,
        "vehicle_details": vd,
        "vehicle_public":  vp,
        "vehicle_docs":    {},                 # Uploaded separately via /items/{id}/vehicle-doc
    }

    result = mongo.items.insert_one(item_doc)

    # ── Generate QR code → save to MinIO ─────────────────────
    qr_url = f"http://localhost:5173/q/{qr_token}"
    img    = qrcode.make(qr_url)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_bytes = buf.getvalue()

    qr_key = minio.qr_codes.put_bytes(qr_bytes, f"{qr_token}.png", "image/png")
    qr_url_presigned = minio.qr_codes.presigned_get(qr_key)

    return False, {
        "status":  True,
        "message": "201 | Item created successfully",
        "data": {
            "item_id":   str(result.inserted_id),
            "qr_token":  qr_token,
            "qr_url":    qr_url_presigned,    # presigned URL to download QR image
            "image_url": minio.uploads.safe_presigned_get(image_key),
        }
    }


async def get_my_items(user, page: int = 1, limit: int = 6):
    skip  = (page - 1) * limit
    total = mongo.items.count_documents({"user_id": user["_id"]})
    logger.debug(f'USER ID : {user["_id"]} , Type : {type(user["_id"])}')
    cursor = mongo.items.find(
        {"user_id": user["_id"]}
    ).sort("_id", -1).skip(skip).limit(limit)

    items = []
    for doc in cursor:
        # Presigned URL for item image
        image_url = minio.uploads.safe_presigned_get(doc.get("image"))
        # Presigned URL for QR code
        qr_key    = f"{doc['qr_token']}.png"
        qr_url    = minio.qr_codes.safe_presigned_get(qr_key)

        items.append({
            "id":        str(doc["_id"]),
            "name":      doc["name"],
            "qr_token":  doc["qr_token"],
            "status":    doc["status"],
            "item_type": doc.get("item_type", "other"),
            "image":     doc.get("image"),      # key
            "image_url": image_url,             # presigned
            "qr_url":    qr_url,                # presigned
        })

    return False, {
        "status":  True,
        "message": "200 | Items fetched",
        "data":    {"items": items, "total": total, "page": page, "limit": limit}
    }


async def delete_item(item_id: str, user):
    doc = mongo.items.find_one({"_id": ObjectId(item_id), "user_id": user["_id"]})
    if not doc:
        return True, {"status": False, "message": "404 | Item not found", "data": None}

    # Delete image from MinIO
    if doc.get("image"):
        try: minio.uploads.delete(doc["image"])
        except Exception: pass

    # Delete QR from MinIO
    try: minio.qr_codes.delete(f"{doc['qr_token']}.png")
    except Exception: pass

    # Delete all vehicle docs from MinIO
    for key in doc.get("vehicle_docs", {}).values():
        if key:
            try: minio.documents.delete(key)
            except Exception: pass

    mongo.items.delete_one({"_id": ObjectId(item_id)})
    return False, {"status": True, "message": "200 | Item deleted", "data": None}


async def update_item(item_id: str, payload, user):
    doc = mongo.items.find_one({"_id": ObjectId(item_id), "user_id": user["_id"]})
    if not doc:
        return True, {"status": False, "message": "404 | Item not found", "data": None}

    mongo.items.update_one(
        {"_id": ObjectId(item_id)},
        {"$set": {"name": payload.name, "description": payload.description}}
    )
    return False, {"status": True, "message": "200 | Item updated", "data": None}


async def toggle_status(item_id, user):
    item = mongo.items.find_one({"_id": ObjectId(item_id), "user_id": user["_id"]})
    if not item:
        return True, {"status": False, "message": "404 | Item not found", "data": None}

    new_status = ITEM_STATUS_LOST if item["status"] == ITEM_STATUS_ACTIVE else ITEM_STATUS_ACTIVE
    mongo.items.update_one({"_id": ObjectId(item_id)}, {"$set": {"status": new_status}})
    return False, {"status": True, "message": "200 | Status updated", "data": {"new_status": new_status}}

# app/services/item_service.py (add the following function)

async def update_item_full(
    item_id: str,
    user,
    name: str,
    description: Optional[str],
    show_phone: bool,
    show_email: bool,
    item_type: str,
    vehicle_details: Optional[str],
    vehicle_public: Optional[str],
    image: Optional[UploadFile]
):
    """
    Fully update an item, including optional image replacement.
    Returns (error, result_dict).
    """
    # 1. Verify item exists and belongs to user
    item = mongo.items.find_one({"_id": ObjectId(item_id), "user_id": user["_id"]})
    if not item:
        logger.warning(f"Item {item_id} not found for user {user['_id']}")
        return True, {"status": False, "message": "404 | Item not found", "data": None}

    # 2. Prepare update dictionary
    update_fields = {
        "name": name,
        "description": description,
        "privacy.show_phone": show_phone,
        "privacy.show_email": show_email,
        "item_type": item_type,
    }

    # 3. Parse JSON fields if provided
    if vehicle_details:
        try:
            vd = json.loads(vehicle_details)
            update_fields["vehicle_details"] = vd
        except json.JSONDecodeError:
            logger.error(f"Invalid vehicle_details JSON: {vehicle_details}")
            return True, {"status": False, "message": "Invalid vehicle_details format", "data": None}

    if vehicle_public:
        try:
            vp = json.loads(vehicle_public)
            update_fields["vehicle_public"] = vp
        except json.JSONDecodeError:
            logger.error(f"Invalid vehicle_public JSON: {vehicle_public}")
            return True, {"status": False, "message": "Invalid vehicle_public format", "data": None}

    # 4. Handle image upload (if a new file is provided)
    if image and image.filename:
        try:
            # Upload new image to MinIO
            new_image_key = await minio.uploads.put_upload_file(image, prefix="items")
            logger.info(f"Uploaded new image for item {item_id}: {new_image_key}")

            # Delete old image if it exists
            old_image = item.get("image")
            if old_image:
                try:
                    minio.uploads.delete(old_image)
                    logger.info(f"Deleted old image {old_image} for item {item_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete old image {old_image}: {e}")

            update_fields["image"] = new_image_key
        except Exception as e:
            logger.error(f"Image upload failed for item {item_id}: {e}")
            return True, {"status": False, "message": "Image upload failed", "data": None}

    # 5. Apply updates to database
    mongo.items.update_one(
        {"_id": ObjectId(item_id)},
        {"$set": update_fields}
    )
    logger.info(f"Item {item_id} updated successfully by user {user['_id']}")

    # 6. Generate presigned URL for the (possibly new) image
    final_image_key = update_fields.get("image") or item.get("image")
    new_image_url = minio.uploads.safe_presigned_get(final_image_key)

    return False, {
        "status": True,
        "message": "200 | Item updated successfully",
        "data": {
            "item_id": item_id,
            "image_url": new_image_url,
        }
    }