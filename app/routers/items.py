# from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
# from loguru import logger
# from bson import ObjectId

# from app.models.item_models import ItemCreate
# from app.services.item_service import create_item, get_my_items, delete_item, update_item, toggle_status
# from app.utils.auth import get_current_user
# from app.constants import Messages



# router = APIRouter(
#     prefix="/items",
#     tags=["Items"]
# )


# @router.post("/create", status_code=201)
# async def create_item_api(
#     name: str = Form(...),
#     description: str = Form(None),
#     show_phone: bool = Form(False),
#     show_email: bool = Form(False),
#     item_type: str  = Form("other"),
#     vehicle_details: str  = Form(None),   # JSON string
#     vehicle_public:  str  = Form(None),
#     image: UploadFile = File(None),
#     user=Depends(get_current_user)
# ):
#     try:
#         logger.info("Create item request received")

#         payload = ItemCreate(
#             name=name,
#             description=description,
#             show_phone=show_phone,
#             show_email=show_email
#         )

#         error, result = await create_item(payload, image, user, item_type, vehicle_details, vehicle_public)

#         if error:
#             raise HTTPException(status_code=400, detail=result["message"])

#         return result

#     except Exception as e:
#         logger.error(f"Create item failed: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=Messages.INTERNAL_SERVER_ERROR_MSG
#         )

# @router.get("/my-items")
# async def my_items(
#     page: int = 1,
#     limit: int = 6,
#     user=Depends(get_current_user)
# ):
#     try:
#         error, result = await get_my_items(user, page, limit)

#         if error:
#             raise HTTPException(
#                 status_code=400,
#                 detail=result["message"]
#             )

#         return result

#     except Exception as e:
#         logger.error(f"Fetch items failed: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=Messages.INTERNAL_SERVER_ERROR_MSG
#         )

# @router.delete("/{item_id}")
# async def delete_item_api(
#     item_id: str,
#     user=Depends(get_current_user)
# ):
#     error, result = await delete_item(item_id, user)

#     if error:
#         raise HTTPException(
#             status_code=404,
#             detail=result["message"]
#         )

#     return result

# @router.put("/{item_id}")
# async def update_item_api(
#     item_id: str,
#     payload: ItemCreate,
#     user=Depends(get_current_user)
# ):
#     error, result = await update_item(item_id, payload, user)

#     if error:
#         raise HTTPException(
#             status_code=404,
#             detail=result["message"]
#         )

#     return result

# @router.patch("/{item_id}/toggle-status")
# async def toggle_item_status(item_id: str, user=Depends(get_current_user)):
#     try:
#         error, result = await toggle_status(item_id, user)
#         if error:
#             raise HTTPException(status_code=400, detail=result["message"])
#         return result
#     except Exception:
#         raise HTTPException(status_code=500, detail=Messages.INTERNAL_SERVER_ERROR_MSG)


# app/routers/items.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional
from loguru import logger
from bson import ObjectId

from app.models.item_models import ItemCreate
from app.services.item_service import create_item, get_my_items, delete_item, update_item, toggle_status, update_item_full
from app.utils.auth import get_current_user
from app.constants import Messages
from app.connectors import mongo, minio

router = APIRouter(prefix="/items", tags=["Items"])

VEHICLE_DOC_TYPES = {
    "rc":        "RC / Registration Certificate",
    "insurance": "Insurance",
    "puc":       "PUC / Pollution Certificate",
    "fitness":   "Fitness Certificate",
    "permit":    "Permit",
    "other":     "Other",
}


# ── Create Item ───────────────────────────────────────────────
@router.post("/create", status_code=201)
async def create_item_api(
    name:            str                    = Form(...),
    description:     str                    = Form(None),
    show_phone:      bool                   = Form(False),
    show_email:      bool                   = Form(False),
    item_type:       str                    = Form("other"),
    vehicle_details: str                    = Form(None),   # JSON string
    vehicle_public:  str                    = Form(None),   # JSON string
    image:           Optional[UploadFile]   = File(None),
    user=Depends(get_current_user)
):
    try:
        payload = ItemCreate(
            name=name, description=description,
            show_phone=show_phone, show_email=show_email
        )
        error, result = await create_item(payload, image, user, item_type, vehicle_details, vehicle_public)
        if error:
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Create item failed: {e}")
        raise HTTPException(status_code=500, detail=Messages.INTERNAL_SERVER_ERROR_MSG)


# ── My Items ──────────────────────────────────────────────────
@router.get("/my-items")
async def my_items(page: int = 1, limit: int = 6, user=Depends(get_current_user)):
    try:
        error, result = await get_my_items(user, page, limit)
        if error:
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Fetch items failed: {e}")
        raise HTTPException(status_code=500, detail=Messages.INTERNAL_SERVER_ERROR_MSG)


# ── Upload Vehicle Document ───────────────────────────────────
@router.post("/{item_id}/vehicle-doc")
async def upload_vehicle_doc(
    item_id:  str,
    doc_type: str        = Form(...),
    file:     UploadFile = File(...),
    user=Depends(get_current_user)
):
    """
    Upload a document (RC, Insurance, PUC etc.) for a specific vehicle item.
    Each call uploads ONE document of a specific type.
    """
    if doc_type not in VEHICLE_DOC_TYPES:
        raise HTTPException(400, f"Invalid doc_type. Must be one of: {list(VEHICLE_DOC_TYPES.keys())}")

    ALLOWED = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
    if file.content_type not in ALLOWED:
        raise HTTPException(400, "Only JPG, PNG, WEBP, PDF allowed")
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large. Max 10MB.")

    # Verify item belongs to this user
    item = mongo.items.find_one({"_id": ObjectId(item_id), "user_id": user["_id"]})
    if not item:
        raise HTTPException(404, "Item not found")
    if item.get("item_type") != "vehicle":
        raise HTTPException(400, "Vehicle documents can only be uploaded for vehicle items")

    try:
        # Delete old doc for this type if exists
        old_key = item.get("vehicle_docs", {}).get(doc_type)
        if old_key:
            try: minio.documents.delete(old_key)
            except Exception: pass

        # Upload to MinIO under items/{item_id}/
        key = await minio.documents.put_upload_file(file, prefix=f"vehicle_docs/{item_id}")
        mongo.items.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": {f"vehicle_docs.{doc_type}": key}}
        )
        return {
            "status":   True,
            "doc_type": doc_type,
            "label":    VEHICLE_DOC_TYPES[doc_type],
            "key":      key,
            "url":      minio.documents.presigned_get(key),
        }
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Vehicle doc upload failed: {e}")
        raise HTTPException(500, "Document upload failed")


# ── Delete Vehicle Document ───────────────────────────────────
@router.delete("/{item_id}/vehicle-doc/{doc_type}")
async def delete_vehicle_doc(item_id: str, doc_type: str, user=Depends(get_current_user)):
    item = mongo.items.find_one({"_id": ObjectId(item_id), "user_id": user["_id"]})
    if not item:
        raise HTTPException(404, "Item not found")
    key = item.get("vehicle_docs", {}).get(doc_type)
    if key:
        try: minio.documents.delete(key)
        except Exception: pass
    mongo.items.update_one(
        {"_id": ObjectId(item_id)},
        {"$unset": {f"vehicle_docs.{doc_type}": ""}}
    )
    return {"status": True, "message": f"{doc_type} removed"}


# ── Get Item with Vehicle Docs (presigned URLs) ───────────────
@router.get("/{item_id}")
async def get_item(item_id: str, user=Depends(get_current_user)):
    item = mongo.items.find_one({"_id": ObjectId(item_id), "user_id": user["_id"]})
    if not item:
        raise HTTPException(404, "Item not found")

    # Presigned URL for item image
    image_url = minio.uploads.safe_presigned_get(item.get("image"))

    # Presigned URLs for vehicle docs
    vehicle_docs_urls = {}
    for doc_type, key in item.get("vehicle_docs", {}).items():
        vehicle_docs_urls[doc_type] = {
            "key":   key,
            "url":   minio.documents.safe_presigned_get(key),
            "label": VEHICLE_DOC_TYPES.get(doc_type, doc_type),
        }

    return {
        "status": True,
        "data": {
            "id":              str(item["_id"]),
            "name":            item["name"],
            "description":     item.get("description"),
            "qr_token":        item["qr_token"],
            "status":          item["status"],
            "item_type":       item.get("item_type", "other"),
            "image":           item.get("image"),
            "image_url":       image_url,
            "vehicle_details": item.get("vehicle_details", {}),
            "vehicle_public":  item.get("vehicle_public",  {}),
            "vehicle_docs":    vehicle_docs_urls,
            "privacy":         item.get("privacy", {}),
        }
    }


# ── Delete Item ───────────────────────────────────────────────
@router.delete("/{item_id}")
async def delete_item_api(item_id: str, user=Depends(get_current_user)):
    error, result = await delete_item(item_id, user)
    if error:
        raise HTTPException(status_code=404, detail=result["message"])
    return result


# ── Update Item ───────────────────────────────────────────────
@router.put("/{item_id}")
async def update_item_api(item_id: str, payload: ItemCreate, user=Depends(get_current_user)):
    error, result = await update_item(item_id, payload, user)
    if error:
        raise HTTPException(status_code=404, detail=result["message"])
    return result


# ── Toggle Status ─────────────────────────────────────────────
@router.patch("/{item_id}/toggle-status")
async def toggle_item_status(item_id: str, user=Depends(get_current_user)):
    try:
        error, result = await toggle_status(item_id, user)
        if error:
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except HTTPException: raise
    except Exception:
        raise HTTPException(status_code=500, detail=Messages.INTERNAL_SERVER_ERROR_MSG)

# app/routers/items.py (add the following new endpoint)

@router.post("/{item_id}/edit", status_code=200)
async def edit_item_api(
    item_id: str,
    name:            str                    = Form(...),
    description:     Optional[str]           = Form(None),
    show_phone:      bool                    = Form(False),
    show_email:      bool                    = Form(False),
    item_type:       str                    = Form("other"),
    vehicle_details: Optional[str]           = Form(None),   # JSON string
    vehicle_public:  Optional[str]           = Form(None),   # JSON string
    image:           Optional[UploadFile]    = File(None),
    user=Depends(get_current_user)
):
    """
    Edit an existing item. Supports updating name, description, privacy settings,
    item type, vehicle details (as JSON), and optionally a new image.
    """
    try:
        error, result = await update_item_full(
            item_id, user,
            name, description,
            show_phone, show_email,
            item_type,
            vehicle_details, vehicle_public,
            image
        )
        if error:
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Edit item failed: {e}")
        raise HTTPException(status_code=500, detail=Messages.INTERNAL_SERVER_ERROR_MSG)