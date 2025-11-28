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

    async def uplaod_biz_image(
        self,
        biz_id: str,
        biz_image: UploadFile,
    ) -> List[str]:
        image_urls = []
        if biz_image:
            image_url = await self.image_service.upload_image(
                file=biz_image,
                folder_name=f"biz/{biz_id}",
            )
            image_urls.append(image_url)
        return image_urls

    # 내 비즈계정 정보 조회
    async def get_my_biz_account_info(self, token: str):
        # 1. 토큰 검증 → biz_id 추출
        biz_id = get_biz_id_from_token(token)

        # 2. DB에서 정보 조회
        biz = await self.biz_repository.get_biz_account_info(biz_id=biz_id)

        if not biz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="존재하지 않는 비즈 계정입니다.",
            )

        return {
            "biz_id": biz[0],
            "store_type": biz[1],
            "tags": biz[2],
            "address": biz[3],
            "business_hours": biz[4],
            "phone_number": biz[5],
            "manager_phone": biz[6],
            "latitude": biz[7],
            "longitude": biz[8],
            "image_urls": biz[9],
        }

    async def upload_biz_images(
        self,
        biz_id: str,
        biz_image: List[UploadFile],
    ) -> List[str]:

        if not biz_image:
            return []

        image_urls = await self.image_service.upload_images(
            user_id=biz_id,
            images=biz_image,
            image_label="biz_profile",
        )
        await self.biz_repository.upload_biz_images(
            biz_id=biz_id,
            image_urls=image_urls,
            start_index=0,
        )

        # 3. 그대로 반환
        return image_urls

    async def delete_biz_account(self, token: str):
        # 토큰을 검증해 biz_id를 받는다
        biz_id = get_biz_id_from_token(token)

        # biz_id로 biz_account 정보를 삭제(비활성화) 한다.
        await self.biz_repository.delete_biz_account(biz_id=biz_id)
        return True

    # 쿠폰 deleted 추가.
    async def create_biz_coupon(
        self,
        token: str,
        title: str,
        content: str,
        start_date: str,
        expired_date: str,
        amount: str,
    ):
        biz_id = get_biz_id_from_token(token)

        coupon = await self.biz_repository.create_biz_coupon(
            biz_id=biz_id,
            title=title,
            content=content,
            start_date=start_date,
            expired_date=expired_date,
            amount=amount,
        )
        return True

    async def update_biz_coupon(
        self,
        token: str,
        title: Optional[str] = None,
    ): ...
