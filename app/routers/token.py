from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.services.user_service import UserService
from app.services.token_service import TokenService
from app.utils.token import create_access_token, create_refresh_token
from jose import jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
router = APIRouter()
user_service = UserService()
token_service = TokenService()


@router.get("/v1/gik-backend/token/{user_id}", status_code=status.HTTP_200_OK)
async def generate_user_token(
    user_id: str,
):
    """
    DB에 유저id를 검색하고, 일치하는 유저에게 토큰을 발급합니다.
    user_id : 발급받는 유저의 ID
    """
    # 유저가 존재하는지 확인
    user = await user_service.fetch_active_user(user_id)
    if not user:
        return {
            "success": False,
            "message": "해당 유저는 존재하지 않거나, 탈퇴한 유저입니다."
        }
    
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    
    success: bool = await token_service.generate_user_token(user_id, access_token, refresh_token)
    if not success:
        return {
            "success": False,
            "message": "토큰 발급에 실패했습니다."
        }
    
    return {
        "success": True,
        "message": "토큰이 성공적으로 발급되었습니다.",
        "user_id": user_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
    }
