from fastapi import APIRouter, Depends, HTTPException
from app.utils.auth import get_current_user
from app.services.dashboard_service import get_dashboard_stats, get_item_wise_scan_stats

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get("/stats")
async def dashboard_stats(user=Depends(get_current_user)):
    error, result = await get_dashboard_stats(user["_id"])

    if error:
        raise HTTPException(
            status_code=result["status_code"],
            detail=result["message"]
        )

    return result

@router.get("/item-scan-stats")
async def item_scan_stats(user=Depends(get_current_user)):
    error, result = await get_item_wise_scan_stats(user["_id"])

    if error:
        raise HTTPException(
            status_code=result["status_code"],
            detail=result["message"]
        )

    return result