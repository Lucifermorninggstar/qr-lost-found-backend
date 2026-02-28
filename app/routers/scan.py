from fastapi import APIRouter, HTTPException
from loguru import logger

from app.services.scan_service import scan_qr
from app.models.scan_models import ScanRequest
from app.constants import Messages

router = APIRouter(
    prefix="/q",
    tags=["QR Scan"]
)


@router.get("/{token}")
async def scan_qr_public(token: str):
    try:
        logger.info(f"QR scanned | token={token}")

        error, result = await scan_qr(token)
        if error:
            raise HTTPException(status_code=404, detail=result["message"])

        return result

    except Exception as e:
        logger.error(f"QR scan failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=Messages.INTERNAL_SERVER_ERROR_MSG
        )


@router.post("/{token}")
async def scan_qr_with_data(token: str, payload: ScanRequest):
    try:
        logger.info(f"QR scanned with data | token={token}")

        error, result = await scan_qr(token, payload)
        if error:
            raise HTTPException(status_code=404, detail=result["message"])

        return result

    except Exception as e:
        logger.error(f"QR scan failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=Messages.INTERNAL_SERVER_ERROR_MSG
        )
