from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer

from app.services.credit_service import CreditManager
from app.utils.token import get_user_id_from_token

oauth2_scheme = HTTPBearer()
router = APIRouter()


@router.get("/v1/gik-backend/credit", status_code=status.HTTP_200_OK)
async def get_credit_end_point(token: str = Depends(oauth2_scheme)) -> dict:
    """현재 보유 중인 크레딧을 조회하는 api endpoint"""
    user_id = await get_user_id_from_token(token)

    credit_manager = CreditManager(user_id)
    credit_balance = await credit_manager.get_credit_balance()

    return {"balance": credit_balance}


@router.get("/v1/gik-backend/credit-history", status_code=status.HTTP_200_OK)
async def get_credit_history_end_point(token: str = Depends(oauth2_scheme)) -> dict:
    """크레딧 증차감 히스토리를 조회하는 api endpoint"""
    user_id = await get_user_id_from_token(token)

    credit_manager = CreditManager(user_id)
    credit_history = await credit_manager.get_credit_history()

    return credit_history
