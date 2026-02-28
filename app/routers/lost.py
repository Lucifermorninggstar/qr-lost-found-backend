from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from app.models.lost_models import LostModeUpdate
from app.services.lost_service import update_lost_mode
from app.utils.auth import get_current_user
from app.constants import Messages

router = APIRouter(
    prefix="/items",
    tags=["Lost Mode"]
)


@router.patch("/{item_id}/lost")
async def set_lost_mode(
    item_id: str,
    payload: LostModeUpdate,
    user=Depends(get_current_user)
):
    try:
        logger.info(f"Lost mode update | item={item_id}")

        error, result = await update_lost_mode(item_id, payload, user)
        if error:
            raise HTTPException(status_code=404, detail=result["message"])

        return result

    except Exception as e:
        logger.error(f"Lost mode update failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=Messages.INTERNAL_SERVER_ERROR_MSG
        )
