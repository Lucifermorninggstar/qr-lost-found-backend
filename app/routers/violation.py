from fastapi import APIRouter, HTTPException
from loguru import logger

from app.models.violation_models import ViolationCreate
from app.services.violation_service import report_violation
from app.constants import Messages

router = APIRouter(
    prefix="/violation",
    tags=["Violation / Parking"]
)


@router.post("/{token}", status_code=201)
async def report_violation_api(token: str, payload: ViolationCreate):
    """
    Public endpoint to report parking / blocking violation
    """
    try:
        logger.info(
            f"Violation reported | token={token} | type={payload.type}"
        )

        error, result = await report_violation(token, payload)

        if error:
            logger.warning(
                f"Violation failed | token={token} | {result['message']}"
            )
            raise HTTPException(
                status_code=int(result["message"].split("|")[0].strip()),
                detail=result["message"]
            )

        return result

    except HTTPException as http_err:
        # 🔥 Important: re-raise HTTP errors (don't convert to 500)
        raise http_err

    except Exception as e:
        logger.error(f"Violation report failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=Messages.INTERNAL_SERVER_ERROR_MSG
        )
