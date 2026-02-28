from fastapi import APIRouter, Depends, HTTPException, Query
from app.utils.auth import get_current_user
from app.services.history_service import (
    get_scan_history,
    get_violation_history
)

router = APIRouter(prefix="/history", tags=["History"])


@router.get("/scans")
async def scans(
    user=Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page")
):
    error, result = await get_scan_history(
        user["_id"], 
        page=page, 
        limit=limit
    )
    if error:
        raise HTTPException(
            status_code=result["status_code"], 
            detail=result["message"]
        )
    return result


@router.get("/violations")
async def violations(
    user=Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page")
):
    error, result = await get_violation_history(
        user["_id"], 
        page=page, 
        limit=limit
    )
    if error:
        raise HTTPException(
            status_code=result["status_code"], 
            detail=result["message"]
        )
    return result
