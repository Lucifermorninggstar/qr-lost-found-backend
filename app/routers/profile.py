# # app/routers/profile.py
# from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
# from bson import ObjectId
# from datetime import datetime
# from loguru import logger

# from app.connectors import mongo, minio
# from app.utils.auth import get_current_user

# router = APIRouter(prefix="/profile", tags=["Profile"])

# ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}

# # VALID_DOCS = {"aadhaar", "pan", "driving_licence", "rc", "insurance", "puc", "other"}
# VALID_DOCS = {"aadhaar", "pan","fitness",  "driving_licence", "rc", "insurance", "puc", "other", "pollution", }

# DOC_LABELS = {
#     "aadhaar":         "Aadhaar Card",
#     "pan":             "PAN Card",
#     "driving_licence": "Driving Licence",
#     "rc":              "RC / Registration",
#     "insurance":       "Insurance",
#     "puc":             "PUC Certificate",
#     "other":           "Other Document",
# }


# def _serialize_user(u: dict) -> dict:
#     created = u.get("created_at")
#     # Convert document keys → presigned URLs
#     raw_docs = u.get("documents", {})
#     docs_with_urls = {}
#     for doc_type, obj_key in raw_docs.items():
#         docs_with_urls[doc_type] = {
#             "key": obj_key,
#             "url": minio.documents.safe_presigned_get(obj_key),
#             "label": DOC_LABELS.get(doc_type, doc_type),
#         }
#     # Profile photo presigned URL
#     photo_key = u.get("photo")
#     photo_url = minio.uploads.safe_presigned_get(photo_key) if photo_key else None

#     return {
#         "id":            str(u["_id"]),
#         "name":          u.get("name", ""),
#         "email":         u.get("email", ""),
#         "phone":         u.get("phone", ""),
#         "photo_key":     photo_key,
#         "photo_url":     photo_url,            # ← presigned URL for frontend
#         "date_of_birth": u.get("date_of_birth"),
#         "address":       u.get("address"),
#         "city":          u.get("city"),
#         "state":         u.get("state"),
#         "pincode":       u.get("pincode"),
#         "documents":     docs_with_urls,       # ← each has key + presigned url
#         "created_at":    created.isoformat() if isinstance(created, datetime) else str(created or ""),
#     }


# # ── GET /profile ──────────────────────────────────────────────
# @router.get("")
# async def get_profile(current_user=Depends(get_current_user)):
#     return {"status": True, "data": _serialize_user(current_user)}


# # ── PATCH /profile ────────────────────────────────────────────
# @router.patch("")
# async def update_profile(
#     name:          str = Form(None),
#     phone:         str = Form(None),
#     date_of_birth: str = Form(None),
#     address:       str = Form(None),
#     city:          str = Form(None),
#     state:         str = Form(None),
#     pincode:       str = Form(None),
#     current_user=Depends(get_current_user)
# ):
#     fields = {k: v for k, v in {
#         "name": name, "phone": phone, "date_of_birth": date_of_birth,
#         "address": address, "city": city, "state": state, "pincode": pincode,
#     }.items() if v is not None}
#     if not fields:
#         raise HTTPException(400, "No fields provided")
#     mongo.users.set_by_id(current_user["_id"], fields)
#     return {"status": True, "message": "Profile updated"}


# # ── POST /profile/photo ───────────────────────────────────────
# @router.post("/photo")
# async def upload_photo(
#     file: UploadFile = File(...),
#     current_user=Depends(get_current_user)
# ):
#     ALLOWED = {"image/jpeg", "image/png", "image/webp"}
#     if file.content_type not in ALLOWED:
#         raise HTTPException(400, "Only JPG, PNG, WEBP allowed for photos")
#     try:
#         # Delete old photo from MinIO if exists
#         old_key = current_user.get("photo")
#         if old_key:
#             try: minio.uploads.delete(old_key)
#             except Exception: pass

#         # Upload new photo
#         key = await minio.uploads.put_upload_file(file, prefix="photos")
#         mongo.users.set_by_id(current_user["_id"], {"photo": key})

#         return {
#             "status": True,
#             "key":    key,
#             "url":    minio.uploads.presigned_get(key),
#         }
#     except HTTPException: raise
#     except Exception as e:
#         logger.error(e)
#         raise HTTPException(500, "Photo upload failed")


# # ── POST /profile/document ────────────────────────────────────
# @router.post("/document")
# async def upload_document(
#     doc_type: str        = Form(...),
#     file:     UploadFile = File(...),
#     current_user=Depends(get_current_user)
# ):
#     if doc_type not in VALID_DOCS:
#         raise HTTPException(400, f"Invalid doc_type. Must be one of: {VALID_DOCS}")
#     ALLOWED = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
#     if file.content_type not in ALLOWED:
#         raise HTTPException(400, "Only JPG, PNG, WEBP, PDF allowed")
#     try:
#         # Delete old doc from MinIO if exists
#         old_key = current_user.get("documents", {}).get(doc_type)
#         if old_key:
#             try: minio.documents.delete(old_key)
#             except Exception: pass

#         # Upload new doc
#         user_id = str(current_user["_id"])
#         key = await minio.documents.put_upload_file(file, prefix=user_id)
#         mongo.users.set_by_id(current_user["_id"], {f"documents.{doc_type}": key})

#         return {
#             "status":   True,
#             "doc_type": doc_type,
#             "key":      key,
#             "url":      minio.documents.presigned_get(key),
#         }
#     except HTTPException: raise
#     except Exception as e:
#         logger.error(e)
#         raise HTTPException(500, "Document upload failed")


# # ── DELETE /profile/document/{doc_type} ──────────────────────
# @router.delete("/document/{doc_type}")
# async def delete_document(doc_type: str, current_user=Depends(get_current_user)):
#     if doc_type not in VALID_DOCS:
#         raise HTTPException(400, "Invalid doc_type")
#     key = current_user.get("documents", {}).get(doc_type)
#     if key:
#         try: minio.documents.delete(key)
#         except Exception: pass
#     mongo.users.unset_field(current_user["_id"], f"documents.{doc_type}")
#     return {"status": True, "message": f"{doc_type} removed"}


# app/routers/profile.py
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from bson import ObjectId
from datetime import datetime
from loguru import logger

from app.connectors import mongo, minio
from app.utils.auth import get_current_user

router = APIRouter(prefix="/profile", tags=["Profile"])

VALID_DOCS = {
    "aadhaar", "pan", "driving_licence", "rc",
    "insurance", "puc", "pollution", "fitness", "other",
}
PERSONAL_DOC_LABELS = {
    "aadhaar":         "Aadhaar Card",
    "pan":             "PAN Card",
    "driving_licence": "Driving Licence",
    "rc":              "RC / Registration",
    "insurance":       "Insurance",
    "puc":             "PUC Certificate",
    "pollution":       "Pollution Certificate",
    "fitness":         "Fitness Certificate",
    "other":           "Other Document",
}
VEHICLE_DOC_LABELS = {
    "rc":        "RC / Registration",
    "insurance": "Insurance",
    "puc":       "PUC / Pollution",
    "fitness":   "Fitness Certificate",
    "permit":    "Permit",
    "other":     "Other",
}
VEHICLE_DOC_TYPES = {"rc", "insurance", "puc", "fitness", "permit", "other"}


def _serialize_personal_docs(raw: dict) -> dict:
    out = {}
    for doc_type, val in (raw or {}).items():
        key = val if isinstance(val, str) else (val or {}).get("key")
        if not key:
            continue
        out[doc_type] = {
            "key":   key,
            "url":   minio.documents.safe_presigned_get(key),
            "label": PERSONAL_DOC_LABELS.get(doc_type, doc_type),
        }
    return out


def _serialize_vehicle_docs(raw: dict) -> dict:
    out = {}
    for doc_type, key in (raw or {}).items():
        if not key:
            continue
        out[doc_type] = {
            "key":   key,
            "url":   minio.documents.safe_presigned_get(key),
            "label": VEHICLE_DOC_LABELS.get(doc_type, doc_type),
        }
    return out


def _serialize_vehicle_item(item: dict) -> dict:
    vd = item.get("vehicle_details", {})
    return {
        "id":          str(item["_id"]),
        "name":        item.get("name", ""),
        "qr_token":    item.get("qr_token", ""),
        "status":      item.get("status", "active"),
        "image_url":   minio.uploads.safe_presigned_get(item.get("image")),
        "vehicle": {
            "type":             vd.get("type"),
            "number":           vd.get("number"),
            "make":             vd.get("make"),
            "model":            vd.get("model"),
            "year":             vd.get("year"),
            "color":            vd.get("color"),
            "rc_number":        vd.get("rc_number"),
            "insurance_expiry": vd.get("insurance_expiry"),
            "puc_expiry":       vd.get("puc_expiry"),
        },
        "vehicle_docs": _serialize_vehicle_docs(item.get("vehicle_docs", {})),
    }


def _serialize_user(u: dict) -> dict:
    created   = u.get("created_at")
    photo_key = u.get("photo")

    vehicle_items = [
        _serialize_vehicle_item(doc)
        for doc in mongo.items.find({"user_id": u["_id"], "item_type": "vehicle"})
    ]

    return {
        "id":            str(u["_id"]),
        "name":          u.get("name", ""),
        "email":         u.get("email", ""),
        "phone":         u.get("phone") or u.get("mobile_number", ""),
        "mobile_number": u.get("mobile_number", ""),
        "photo_key":     photo_key,
        "photo_url":     minio.uploads.safe_presigned_get(photo_key) if photo_key else None,
        "date_of_birth": u.get("date_of_birth"),
        "address":       u.get("address"),
        "city":          u.get("city"),
        "state":         u.get("state"),
        "pincode":       u.get("pincode"),
        "documents":     _serialize_personal_docs(u.get("documents", {})),
        "vehicle_items": vehicle_items,
        "created_at":    created.isoformat() if isinstance(created, datetime) else str(created or ""),
    }


@router.get("")
async def get_profile(current_user=Depends(get_current_user)):
    return {"status": True, "data": _serialize_user(current_user)}


@router.patch("")
async def update_profile(
    name:          str = Form(None),
    phone:         str = Form(None),
    date_of_birth: str = Form(None),
    address:       str = Form(None),
    city:          str = Form(None),
    state:         str = Form(None),
    pincode:       str = Form(None),
    current_user=Depends(get_current_user)
):
    fields = {k: v for k, v in {
        "name": name, "phone": phone, "date_of_birth": date_of_birth,
        "address": address, "city": city, "state": state, "pincode": pincode,
    }.items() if v is not None}
    if not fields:
        raise HTTPException(400, "No fields provided")
    mongo.users.set_by_id(current_user["_id"], fields)
    return {"status": True, "message": "Profile updated"}


@router.post("/photo")
async def upload_photo(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(400, "Only JPG, PNG, WEBP allowed")
    try:
        old_key = current_user.get("photo")
        if old_key:
            try: minio.uploads.delete(old_key)
            except Exception: pass
        key = await minio.uploads.put_upload_file(file, prefix="photos")
        mongo.users.set_by_id(current_user["_id"], {"photo": key})
        return {"status": True, "key": key, "url": minio.uploads.presigned_get(key)}
    except HTTPException: raise
    except Exception as e:
        logger.error(e); raise HTTPException(500, "Photo upload failed")


@router.post("/document")
async def upload_document(
    doc_type: str = Form(...), file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    if doc_type not in VALID_DOCS:
        raise HTTPException(400, f"Invalid doc_type. Allowed: {sorted(VALID_DOCS)}")
    if file.content_type not in {"image/jpeg","image/png","image/webp","application/pdf"}:
        raise HTTPException(400, "Only JPG, PNG, WEBP, PDF allowed")
    try:
        raw     = current_user.get("documents", {}).get(doc_type)
        old_key = raw if isinstance(raw, str) else (raw or {}).get("key")
        if old_key:
            try: minio.documents.delete(old_key)
            except Exception: pass
        user_id = str(current_user["_id"])
        key = await minio.documents.put_upload_file(file, prefix=f"personal/{user_id}")
        mongo.users.set_by_id(current_user["_id"], {f"documents.{doc_type}": key})
        return {"status": True, "doc_type": doc_type, "key": key, "url": minio.documents.presigned_get(key)}
    except HTTPException: raise
    except Exception as e:
        logger.error(e); raise HTTPException(500, "Document upload failed")


@router.delete("/document/{doc_type}")
async def delete_document(doc_type: str, current_user=Depends(get_current_user)):
    if doc_type not in VALID_DOCS:
        raise HTTPException(400, "Invalid doc_type")
    raw = current_user.get("documents", {}).get(doc_type)
    key = raw if isinstance(raw, str) else (raw or {}).get("key")
    if key:
        try: minio.documents.delete(key)
        except Exception: pass
    mongo.users.unset_field(current_user["_id"], f"documents.{doc_type}")
    return {"status": True, "message": f"{doc_type} removed"}


@router.post("/vehicle/{item_id}/doc")
async def upload_vehicle_doc(
    item_id: str, doc_type: str = Form(...), file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    if doc_type not in VEHICLE_DOC_TYPES:
        raise HTTPException(400, f"Invalid doc_type. Allowed: {sorted(VEHICLE_DOC_TYPES)}")
    if file.content_type not in {"image/jpeg","image/png","image/webp","application/pdf"}:
        raise HTTPException(400, "Only JPG, PNG, WEBP, PDF allowed")
    item = mongo.items.find_one({"_id": ObjectId(item_id), "user_id": current_user["_id"]})
    if not item:
        raise HTTPException(404, "Vehicle not found")
    if item.get("item_type") != "vehicle":
        raise HTTPException(400, "Not a vehicle item")
    try:
        old_key = item.get("vehicle_docs", {}).get(doc_type)
        if old_key:
            try: minio.documents.delete(old_key)
            except Exception: pass
        key = await minio.documents.put_upload_file(file, prefix=f"vehicle_docs/{item_id}")
        mongo.items.update_one({"_id": ObjectId(item_id)}, {"$set": {f"vehicle_docs.{doc_type}": key}})
        return {"status": True, "doc_type": doc_type,
                "label": VEHICLE_DOC_LABELS.get(doc_type, doc_type),
                "key": key, "url": minio.documents.presigned_get(key)}
    except HTTPException: raise
    except Exception as e:
        logger.error(e); raise HTTPException(500, "Vehicle doc upload failed")


@router.delete("/vehicle/{item_id}/doc/{doc_type}")
async def delete_vehicle_doc(item_id: str, doc_type: str, current_user=Depends(get_current_user)):
    item = mongo.items.find_one({"_id": ObjectId(item_id), "user_id": current_user["_id"]})
    if not item:
        raise HTTPException(404, "Vehicle not found")
    key = item.get("vehicle_docs", {}).get(doc_type)
    if key:
        try: minio.documents.delete(key)
        except Exception: pass
    mongo.items.update_one({"_id": ObjectId(item_id)}, {"$unset": {f"vehicle_docs.{doc_type}": ""}})
    return {"status": True, "message": f"{doc_type} removed"}