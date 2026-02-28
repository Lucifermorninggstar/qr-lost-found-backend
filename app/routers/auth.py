# from fastapi import APIRouter, HTTPException, Depends
# from fastapi.security import OAuth2PasswordRequestForm
# from loguru import logger

# from app.models.user_models import UserCreate, UserLogin
# from app.services.auth_service import create_user, login_user
# from app.constants import Messages
# from app.utils.auth import get_current_user 

# router = APIRouter(prefix="/auth", tags=["Auth"])

# @router.post("/token")
# async def token(form_data: OAuth2PasswordRequestForm = Depends()):
#     """
#     Swagger OAuth2 compatible login
#     """
#     payload = type(
#         "LoginPayload",
#         (),
#         {
#             "email": form_data.username,
#             "password": form_data.password
#         }
#     )

#     error, result = await login_user(payload)
#     if error:
#         raise HTTPException(status_code=401, detail=result["message"])

#     return {
#         "access_token": result["data"]["access_token"],
#         "token_type": "bearer"
#     }


# @router.post("/create-user", status_code=201)
# async def create_users(user: UserCreate):
#     """
#     Endpoint to create a new user.
#     """
#     try:
#         logger.info("Received request to create user")

#         error, result = await create_user(user)
#         if error:
#             logger.warning(f"User creation failed: {result['message']}")
#             raise HTTPException(status_code=400, detail=result["message"])

#         logger.info("User created successfully")
#         return result

#     except Exception as e:
#         logger.error(f"Unexpected error while creating user: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=Messages.INTERNAL_SERVER_ERROR_MSG
#         )


# @router.post("/login")
# async def login(user: UserLogin):
#     try:
#         logger.info("Login request received")

#         error, result = await login_user(user)
#         if error:
#             raise HTTPException(status_code=401, detail=result["message"])

#         return result

#     except Exception as e:
#         logger.error(f"Login error: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=Messages.INTERNAL_SERVER_ERROR_MSG
#         )

# @router.get("/me")
# async def get_me(user=Depends(get_current_user)):
#     return {
#         "status": True,
#         "status_code": 200,
#         "data": {
#             "name": user["name"],
#             "email": user["email"],
#             "mobile_number": user.get("mobile_number"),
#             "photo": user.get("photo")
#         }
#     }


# app/routers/auth.py
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional
from loguru import logger

from app.models.user_models import UserLogin
from app.services.auth_service import create_user, login_user
from app.constants import Messages
from app.utils.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


# ── Swagger OAuth2 ────────────────────────────────────────────
@router.post("/token")
async def token(form_data: OAuth2PasswordRequestForm = Depends()):
    payload = type("P", (), {"email": form_data.username, "password": form_data.password})
    error, result = await login_user(payload)
    if error:
        raise HTTPException(status_code=401, detail=result["message"])
    return {"access_token": result["data"]["access_token"], "token_type": "bearer"}


# ── Signup — FormData (supports photo upload) ─────────────────
@router.post("/create-user", status_code=201)
async def create_users(
    # Mandatory
    name:          str           = Form(...),
    email:         str           = Form(...),
    mobile_number: str           = Form(...),
    password:      str           = Form(...),
    # Optional personal
    date_of_birth: Optional[str] = Form(None),
    address:       Optional[str] = Form(None),
    city:          Optional[str] = Form(None),
    state:         Optional[str] = Form(None),
    pincode:       Optional[str] = Form(None),
    # Optional photo
    photo:         Optional[UploadFile] = File(None),
):
    try:
        logger.info(f"Signup request: {email}")
        # Build a simple object to pass to service
        payload = type("P", (), {
            "name":          name,
            "email":         email,
            "mobile_number": mobile_number,
            "password":      password,
            "date_of_birth": date_of_birth,
            "address":       address,
            "city":          city,
            "state":         state,
            "pincode":       pincode,
            "photo":         photo,       # UploadFile or None
        })
        error, result = await create_user(payload)
        if error:
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(status_code=500, detail=Messages.INTERNAL_SERVER_ERROR_MSG)


# ── Login ─────────────────────────────────────────────────────
@router.post("/login")
async def login(user: UserLogin):
    try:
        error, result = await login_user(user)
        if error:
            raise HTTPException(status_code=401, detail=result["message"])
        return result
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=Messages.INTERNAL_SERVER_ERROR_MSG)


# ── Me ────────────────────────────────────────────────────────
@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    from app.connectors import minio
    photo_key = user.get("photo")
    return {
        "status": True,
        "data": {
            "_id":          str(user["_id"]),
            "name":         user["name"],
            "email":        user["email"],
            "mobile_number":user.get("mobile_number"),
            "photo":        photo_key,
            "photo_url":    minio.uploads.safe_presigned_get(photo_key) if photo_key else None,
        }
    }