from typing import Optional, List
from fastapi import HTTPException, status, UploadFile, File
from app.utils.logging_config import get_logger
from app.repository.biz_repository import BizRepository
from app.services.image_service import ImageService
from app.db.biz import BizProfileResponse
from app.utils.security import verify_password, hash_password
from app.utils.token import (
    create_access_token_biz,
    create_refresh_token_biz,
    get_biz_id_from_token,
    get_user_id_from_token,
    create_refresh_token,
    create_access_token,
)
import json

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
        # 유저 ID
        user_id = biz[1]
        # 비밀번호
        stored_hash = biz[3]
        # 1. 아이디가 다를경우, PW가 다를경우, 그리고 PW decode 과정이 필요하다.
        if not verify_password(biz_password, stored_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="비밀번호가 일치하지 않습니다.",
            )

        access_token = create_access_token(user_id=user_id)
        refresh_token = create_refresh_token(user_id=user_id)

        await self.biz_repository.update_biz_tokens(
            biz_id=biz_id,
            access_token=access_token,
            refresh_token=refresh_token,
        )
        return access_token, refresh_token

    async def get_my_biz_account_info(self, token: str):
        user_id = await get_user_id_from_token(token)
        biz = await self.biz_repository.get_my_biz_account_info(user_id=user_id)

        if not biz:
            raise HTTPException(
                status_code=404, detail="존재하지 않는 비즈 계정입니다."
            )

        return BizProfileResponse(
            id=biz.id,
            bizId=biz.biz_id,
            storeType=biz.store_type,
            storeName=biz.store_name,
            tags=biz.tags,
            address=biz.address,
            businessHours=biz.business_hours,
            phoneNumber=biz.phone,
            managerPhone=biz.manager_phone,
            latitude=biz.latitude,
            longitude=biz.longitude,
            fcm=biz.fcm,
            credit=biz.credit,
            marketingAgree=biz.marketing_agree,
            nightAgree=biz.night_agree,
            personalChatAlarmAgree=biz.personal_chat_alarm_agree,
            groupChatAlarmAgree=biz.group_chat_alarm_agree,
            postCommentAlarmAgree=biz.post_comment_alarm_agree,
            postLikeAlarmAgree=biz.post_like_alarm_agree,
            profileAlarmAgree=biz.profile_alarm_agree,
            feedLikeAlarmAgree=biz.feed_like_alarm_agree,
            feedCommentAlarmAgree=biz.feed_comment_alarm_agree,
            profileImage=json.loads(biz.image_urls) if biz.image_urls else [],
            blockUserList=(
                json.loads(biz.block_user_list) if biz.block_user_list else []
            ),
            favoriteUserList=(
                json.loads(biz.favorite_user_list) if biz.favorite_user_list else []
            ),
            pushRead=biz.push_read,
            profileRead=biz.profile_read,
            hasSecretFeed=biz.has_secret_feed,
        )

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

    async def create_biz_coupon(
        self,
        token: str,
        title: str,
        content: str,
        amount: str,
        start_date: str,
        expired_date: str,
    ):
        user_id = await get_user_id_from_token(token)
        biz_id = await self.biz_repository.get_biz_id(user_id)

        coupon = await self.biz_repository.create_biz_coupon(
            biz_id=biz_id,
            title=title,
            content=content,
            amount=amount,
            start_date=start_date,
            expired_date=expired_date,
        )
        return True

    async def update_biz_coupon(
        self,
        token: str,
        coupon_id: int,
        title: str,
        content: str,
        amount: str,
        start_date: str,
        expired_date: str,
    ):
        user_id = await get_user_id_from_token(token)
        biz_id = await self.biz_repository.get_biz_id(user_id)

        result = await self.biz_repository.update_biz_coupon(
            biz_id=biz_id,
            coupon_id=coupon_id,
            title=title,
            content=content,
            amount=amount,
            start_date=start_date,
            expired_date=expired_date,
        )

        if result is False:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="존재하지 않는 쿠폰이거나 수정 권한이 없습니다.",
            )

        return True

    async def delete_biz_coupon(
        self,
        token: str,
        coupon_id: int,
    ):
        user_id = await get_user_id_from_token(token)
        biz_id = await self.biz_repository.get_biz_id(user_id)

        result = await self.biz_repository.delete_biz_coupon(
            biz_id=biz_id,
            coupon_id=coupon_id,
        )
        if result is False:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="존재하지 않는 쿠폰이거나 삭제 권한이 없습니다.",
            )

        return True
