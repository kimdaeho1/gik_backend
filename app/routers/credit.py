from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer

from app.services.credit_service import CreditManager
from app.utils.token import get_user_id_from_token

oauth2_scheme = HTTPBearer()
router = APIRouter(prefix="/v1/gik-backend", tags=["Credit"])


@router.get("/credit", status_code=status.HTTP_200_OK)
async def get_credit_end_point(token: str = Depends(oauth2_scheme)) -> dict:
    """
    현재 보유 중인 크레딧을 조회
    user_id: 토큰에서 추출한 user_id
    """
    user_id = await get_user_id_from_token(token.credentials)

    credit_manager = CreditManager(user_id)
    credit_balance = await credit_manager.get_credit_balance()

    return {"balance": credit_balance}


@router.get("/credit-history/test", status_code=status.HTTP_200_OK)
async def get_credit_history_end_point(token: str = Depends(oauth2_scheme)) -> dict:
    """
    현재 크레딧 내역을 조회
    user_id: 토큰에서 추출한 user_id
    """
    user_id = await get_user_id_from_token(token.credentials)

    credit_manager = CreditManager(user_id)
    credit_history = await credit_manager.get_credit_history()

    return credit_history
