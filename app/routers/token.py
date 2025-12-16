from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.user_service import UserService
from app.repository.user_repository import UserRepository
from app.services.token_service import TokenService
from dependency_injector.wiring import inject, Provide
from app.core.container import Container
from app.utils.token import (
    create_access_token,
    create_refresh_token,
    create_new_tokens_based_on_refresh_token,
    get_user_id_from_token,
    JWTBearer,
)
from jose import jwt
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

oauth2_scheme = HTTPBearer()
router = APIRouter(prefix="/v1/gik-backend/token", tags=["Token"])


# TODO: expired_in을 어떻게 처리할지.
@router.get("/refresh", status_code=status.HTTP_200_OK)
@inject
async def refresh_token(
    token: str = Depends(oauth2_scheme),
    token_service: TokenService = Depends(Provide[Container.token_service]),
):
    """
    리프레시 토큰을 사용해 새로운 엑세스 토큰과 리프레스 토큰 발급
    token : 기존의 리프레시 토큰
    """
    new_tokens = create_new_tokens_based_on_refresh_token(token.credentials)
    success: bool = await token_service.refresh_user_token(
        new_tokens["user_id"], new_tokens["access_token"], new_tokens["refresh_token"]
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="잘못되거나 만료된 토큰입니다.",
        )
    return {
        "success": True,
        "message": "새 토큰이 발급되었습니다",
        "access_token": new_tokens["access_token"],
        "refresh_token": new_tokens["refresh_token"],
    }


@router.get("/{user_id}", status_code=status.HTTP_200_OK)
@inject
async def generate_user_token(
    user_id: str,
    user_repository: UserRepository = Depends(Provide[Container.user_repository]),
    token_service: TokenService = Depends(Provide[Container.token_service]),
):
    """
    DB에 유저id를 검색하고, 일치하는 유저에게 토큰 발급
    user_id : 발급받는 유저의 ID
    """
    # 유저가 존재하는지 확인
    user = await user_repository.fetch_active_user(user_id)
    if not user:
        return {
            "success": False,
            "message": "해당 유저는 존재하지 않거나, 탈퇴한 유저입니다.",
        }

    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)

    success: bool = await token_service.generate_user_token(
        user_id, access_token, refresh_token
    )
    if not success:
        return {"success": False, "message": "토큰 발급에 실패했습니다."}

    return {
        "success": True,
        "message": "토큰이 성공적으로 발급되었습니다.",
        "user_id": user_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


@router.post("/logout", status_code=status.HTTP_200_OK)
@inject
async def logout_user(
    token: str = Depends(oauth2_scheme),
    token_service: TokenService = Depends(Provide[Container.token_service]),
):
    """
    DB 에서 해당 유저의 액세스 토큰과 리프레시 토큰 제거
    token : 로그아웃할 유저의 액세스 토큰
    """
    # 토큰에서 유저 ID 추출
    user_id = await get_user_id_from_token(token.credentials)

    # 유저 로그아웃
    success = await token_service.logout_user(user_id)
    if not success:
        logger.error(f"로그아웃 실패 for user_id: {user_id}"),
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그아웃 실패",
        )

    return {"success": True, "message": "로그아웃이 완료되었습니다."}
