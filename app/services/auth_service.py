# from loguru import logger
# from app.database import users_collection
# from app.utils.security import hash_password, create_access_token, verify_password
# from datetime import datetime
# from app.connectors import mongo, minio

# async def create_user(payload):
#     logger.info(f"Creating user: {payload.email} | Mobile: {payload.mobile_number}")
    
#     # Check existing user
#     existing = mongo.users.find_one({
#         "$or": [
#             {"email": payload.email},
#             {"mobile_number": payload.mobile_number}
#         ]
#     })
    
#     if existing:
#         logger.warning(f"User already exists: {payload.email} or {payload.mobile_number}")
#         return True, {
#             "status": False,
#             "message": "400 | Email or Mobile already registered",
#             "data": None
#         }
    
#     # Create user document
#     user_doc = {
#         "name": payload.name,
#         "email": payload.email,
#         "mobile_number": payload.mobile_number,
#         "password": hash_password(payload.password),
#         "photo": None,
#         "date_of_birth": payload.date_of_birth,
#         "address": payload.address, 
#         "city": payload.city,
#         "state": payload.state, 
#         "pincode": payload.pincode,
#         "documents": {},
#         "created_at": datetime.utcnow(),
#     }
    
#     logger.info(f"Inserting new user document for {payload.email}")
#     result = mongo.users.insert_one(user_doc)
    
#     if result.inserted_id:
#         logger.info(f"User created successfully: {str(result.inserted_id)}")
#         token = create_access_token({"user_id": str(result.inserted_id)})
#         logger.info(f"Access token generated for user {payload.email}")
        
#         return False, {
#             "status": True,
#             "message": "201 | User created successfully",
#             "data": {"access_token": token}
#         }
#     else:
#         logger.error(f"Failed to insert user: {payload.email}")
#         return True, {
#             "status": False,
#             "message": "500 | Failed to create user",
#             "data": None
#         }

# async def login_user(payload):
#     logger.info(f"Login attempt for email: {payload.email}")
    
#     user = mongo.users.find_one({"email": payload.email})
    
#     if not user:
#         logger.warning(f"User not found: {payload.email}")
#         return True, {
#             "status": False,
#             "message": "401 | Invalid email or password",
#             "data": None
#         }
    
#     logger.info(f"User found: {payload.email}, verifying password...")
#     if not verify_password(payload.password, user["password"]):
#         logger.warning(f"Invalid password for user: {payload.email}")
#         return True, {
#             "status": False,
#             "message": "401 | Invalid email or password",
#             "data": None
#         }
    
#     token = create_access_token({"user_id": str(user["_id"])})
#     logger.info(f"Login successful for user: {payload.email}")
    
#     return False, {
#         "status": True,
#         "message": "200 | Login successful",
#         "data": {"access_token": token}
#     }


# app/services/auth_service.py
from loguru import logger
from datetime import datetime
from app.connectors import mongo, minio
from app.utils.security import hash_password, create_access_token, verify_password


async def create_user(payload):
    logger.info(f"Creating user: {payload.email}")

    existing = mongo.users.find_one({
        "$or": [
            {"email":         payload.email},
            {"mobile_number": payload.mobile_number}
        ]
    })
    if existing:
        return True, {"status": False, "message": "400 | Email or Mobile already registered", "data": None}

    # Upload photo to MinIO if provided
    photo_key = None
    if getattr(payload, "photo", None) and payload.photo.filename:
        try:
            photo_key = await minio.uploads.put_upload_file(payload.photo, prefix="photos")
            logger.info(f"Profile photo uploaded: {photo_key}")
        except Exception as e:
            logger.warning(f"Photo upload failed during signup (non-fatal): {e}")

    user_doc = {
        "name":          payload.name,
        "email":         payload.email,
        "mobile_number": payload.mobile_number,
        "password":      hash_password(payload.password),
        "photo":         photo_key,          # MinIO object key
        "date_of_birth": getattr(payload, "date_of_birth", None),
        "address":       getattr(payload, "address",       None),
        "city":          getattr(payload, "city",          None),
        "state":         getattr(payload, "state",         None),
        "pincode":       getattr(payload, "pincode",       None),
        "documents":     {},
        "created_at":    datetime.utcnow(),
    }

    result = mongo.users.insert_one(user_doc)

    if result.inserted_id:
        token = create_access_token({"user_id": str(result.inserted_id)})
        return False, {
            "status":  True,
            "message": "201 | User created successfully",
            "data":    {"access_token": token}
        }

    return True, {"status": False, "message": "500 | Failed to create user", "data": None}


async def login_user(payload):
    user = mongo.users.find_one({"email": payload.email})
    if not user or not verify_password(payload.password, user["password"]):
        return True, {"status": False, "message": "401 | Invalid email or password", "data": None}

    token = create_access_token({"user_id": str(user["_id"])})
    return False, {
        "status":  True,
        "message": "200 | Login successful",
        "data":    {"access_token": token}
    }