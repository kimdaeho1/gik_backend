from typing import Optional, List
from fastapi import HTTPException, status, UploadFile, File
from app.utils.logging_config import get_logger
from app.repository.biz_repository import BizRepository
from app.services.image_service import ImageService
from app.utils.security import verify_password, hash_password
from app.utils.token import (
    create_access_token_biz,
    create_refresh_token_biz,
    get_biz_id_from_token,
)

logger = get_logger(__name__)


class BizService:
    def __init__(self, biz_repository: BizRepository, image_service: ImageService):
        self.biz_repository = biz_repository
        self.image_service = image_service

    async def login_biz_account(
        self,
        biz_id: str,
        biz_password: str,
    ):
        # ID와 PW 검증 로직
        biz = await self.biz_repository.get_biz_account(biz_id=biz_id)
        if not biz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="존재하지 않는 비즈 계정입니다.",
            )

        # 비밀번호
        stored_hash = biz[2]

        # 1. 아이디가 다를경우, PW가 다를경우, 그리고 PW decode 과정이 필요하다.

        if not verify_password(biz_password, stored_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="비밀번호가 일치하지 않습니다.",
            )

        access_token = create_access_token_biz(biz_id=biz_id)
        refresh_token = create_refresh_token_biz(biz_id=biz_id)

        await self.biz_repository.update_biz_tokens(
            biz_id=biz_id,
            access_token=access_token,
            refresh_token=refresh_token,
        )
        return access_token, refresh_token
        # 로그인 성공. 토큰 발급 로직.

    async def get_biz_account_info(self, token: str):
        # 토큰을 검증해 biz_id를 받는다

        # biz_id로 biz_account 정보를 가져온다.
        ...

    async def update_biz_account_info(
        self,
        token: str,
        biz_name: Optional[str] = None,
        biz_tag: Optional[str] = None,
        biz_phone: Optional[str] = None,
        biz_ddamdangja: Optional[str] = None,
        biz_image: Optional[UploadFile] = File(default=None),
    ):
        # 토큰을 검증해 biz_id를 받는다

        # biz_id로 biz_account 정보를 업데이트 한다.
        ...

    async def delete_biz_account(self, token: str):
        # 토큰을 검증해 biz_id를 받는다

        # biz_id로 biz_account 정보를 삭제(비활성화) 한다.
        ...

    # 비즈 계정 회원가입(만들어는 두는데, 아마도 taily 폼으로 받은 후에 병현님이 직접 넣으실듯.)
    async def create_biz_account(
        self,
        biz_id: str,
        biz_password: str,
        biz_name: str,
        biz_tag: str,
        biz_location: str,
        biz_phone: str,
        biz_ddamdangja: str,
        biz_image: Optional[UploadFile] = File(default=[]),
    ):
        # 비즈 이름 검사: 같은 엄장의 이름이 있는 경우 409 CONFLICT.

        # 비즈 계정을 db에 생성.
        ...
