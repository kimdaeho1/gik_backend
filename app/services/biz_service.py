from typing import Optional, List
from fastapi import HTTPException, status, UploadFile, File
from app.utils.logging_config import get_logger
from app.repository.biz_repository import BizRepository
from app.services.image_service import ImageService
from app.db.biz import (
    BizProfileResponse,
    BizCouponResponse,
    BizDetailResponse,
    BizDetailRow,
    BizCouponRow,
)
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
        user_id = biz[2]
        # 비밀번호
        stored_hash = biz[4]
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

        following_list = json.loads(biz.following_list) if biz.following_list else []
        use_coupon_list = json.loads(biz.use_coupon_list) if biz.use_coupon_list else []

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
            credit=biz.credit,
            marketingAlarm=biz.marketing_agree,
            nightAlarm=biz.night_agree,
            personalChatAlarm=biz.personal_chat_alarm_agree,
            groupChatAlarm=biz.group_chat_alarm_agree,
            postCommentAlarm=biz.post_comment_alarm_agree,
            postLikeAlarm=biz.post_like_alarm_agree,
            profileAlarm=biz.profile_alarm_agree,
            secretAlarm=biz.secret_alarm_agree,
            feedLikeAlarm=biz.feed_like_alarm_agree,
            feedCommentAlarm=biz.feed_comment_alarm_agree,
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
            followerCount=biz.follower_count,
            followingCount=biz.following_count,
            followingList=following_list,
            useCouponList=use_coupon_list,
        )

    async def get_biz_detail(self, biz_id: str):
        biz = await self.biz_repository.get_biz_detail(biz_id=biz_id)

        if not biz:
            raise HTTPException(
                status_code=404, detail="존재하지 않는 비즈 계정입니다."
            )

        coupons = []
        if biz.coupons:
            for coupon in biz.coupons:
                remain_amount = coupon.amount - coupon.use_amount
                coupons.append(
                    BizCouponResponse(
                        id=coupon.id,
                        bizId=coupon.biz_id,
                        title=coupon.title,
                        content=coupon.content,
                        amount=coupon.amount,
                        remainAmount=remain_amount,
                        startDate=coupon.start_date,
                        expiredDate=coupon.expired_date,
                    )
                )

        return BizDetailResponse(
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
            credit=biz.credit,
            marketingAlarm=biz.marketing_agree,
            nightAlarm=biz.night_agree,
            personalChatAlarm=biz.personal_chat_alarm_agree,
            groupChatAlarm=biz.group_chat_alarm_agree,
            postCommentAlarm=biz.post_comment_alarm_agree,
            postLikeAlarm=biz.post_like_alarm_agree,
            profileAlarm=biz.profile_alarm_agree,
            secretAlarm=biz.secret_alarm_agree,
            feedLikeAlarm=biz.feed_like_alarm_agree,
            feedCommentAlarm=biz.feed_comment_alarm_agree,
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
            followerCount=biz.follower_count,
            followingCount=biz.following_count,
            coupons=coupons,
            useCouponList=biz.use_coupon_list,
        )

    async def fetch_biz_list(self, page: int) -> List[BizDetailResponse]:
        rows, columns = await self.biz_repository.fetch_biz_list(page)

        result = []

        for row in rows:
            row_dict = dict(zip(columns, row))

            coupon_json = json.loads(row_dict["coupons"]) if row_dict["coupons"] else []

            coupon_rows = [
                BizCouponRow(
                    id=c["id"],
                    biz_id=c["biz_id"],
                    title=c["title"],
                    content=c["content"],
                    amount=c["amount"],
                    use_amount=c["use_amount"],
                    start_date=c["start_date"],
                    expired_date=c["expired_date"],
                )
                for c in coupon_json
            ]

            row_dict["coupons"] = coupon_rows

            biz = BizDetailRow(**row_dict)

            result.append(
                BizDetailResponse(
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
                    credit=biz.credit,
                    marketingAlarm=biz.marketing_agree,
                    nightAlarm=biz.night_agree,
                    personalChatAlarm=biz.personal_chat_alarm_agree,
                    groupChatAlarm=biz.group_chat_alarm_agree,
                    postCommentAlarm=biz.post_comment_alarm_agree,
                    postLikeAlarm=biz.post_like_alarm_agree,
                    profileAlarm=biz.profile_alarm_agree,
                    secretAlarm=biz.secret_alarm_agree,
                    feedLikeAlarm=biz.feed_like_alarm_agree,
                    feedCommentAlarm=biz.feed_comment_alarm_agree,
                    profileImage=json.loads(biz.image_urls) if biz.image_urls else [],
                    blockUserList=(
                        json.loads(biz.block_user_list) if biz.block_user_list else []
                    ),
                    favoriteUserList=(
                        json.loads(biz.favorite_user_list)
                        if biz.favorite_user_list
                        else []
                    ),
                    pushRead=biz.push_read,
                    profileRead=biz.profile_read,
                    hasSecretFeed=biz.has_secret_feed,
                    followerCount=biz.follower_count,
                    followingCount=biz.following_count,
                    coupons=[
                        BizCouponResponse(
                            id=c.id,
                            bizId=c.biz_id,
                            title=c.title,
                            content=c.content,
                            amount=c.amount,
                            remainAmount=((c.amount or 0) - (c.use_amount or 0)),
                            startDate=c.start_date,
                            expiredDate=c.expired_date,
                        )
                        for c in (biz.coupons or [])
                    ],
                    useCouponList=biz.use_coupon_list,
                )
            )

        return result

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

        coupon = await self.biz_repository.create_biz_coupon(
            biz_id=user_id,
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

        result = await self.biz_repository.update_biz_coupon(
            biz_id=user_id,
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

        result = await self.biz_repository.delete_biz_coupon(
            biz_id=user_id,
            coupon_id=coupon_id,
        )
        if result is False:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="존재하지 않는 쿠폰이거나 삭제 권한이 없습니다.",
            )

        return True

    async def fetch_biz_coupons(
        self,
        token: str,
    ):
        user_id = await get_user_id_from_token(token)

        coupons = await self.biz_repository.fetch_biz_coupons(biz_id=user_id)
        coupon_list = []
        for coupon in coupons:
            remain_amount = coupon.amount - coupon.use_amount
            coupon_list.append(
                BizCouponResponse(
                    id=coupon.id,
                    bizId=coupon.biz_id,
                    title=coupon.title,
                    content=coupon.content,
                    amount=coupon.amount,
                    remainAmount=remain_amount,
                    startDate=coupon.start_date,
                    expiredDate=coupon.expired_date,
                )
            )
        return coupon_list

    async def answer_biz_review(
        self,
        token: str,
        review_id: int,
        answer: str,
    ):
        user_id = await get_user_id_from_token(token)
        biz_id = await self.biz_repository.get_biz_id(user_id)

        result = await self.biz_repository.answer_biz_review(
            biz_id=biz_id,
            review_id=review_id,
            content=answer,
        )
        if result is False:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="존재하지 않는 리뷰이거나 답변 권한이 없습니다.",
            )

        return True
