from fastapi import UploadFile, HTTPException
from datetime import datetime
from app.utils.s3_upload import upload_file_to_s3, CLOUDFRONT_URL, generate_filename
from app.db.user import (
    Hashtags,
    UserProfileResponse,
    UserDetailResponse,
    UserListResponse,
    UserCreateRequest,
    NoAuthUserCreateRequest,
    UserCreditHistoryResponse,
    BizDetailResponse,
    BizReviewResponse,
)
from app.db.image import UserSecretResponse
from app.db.db_connection import db
from typing import List, Optional
from app.utils.logging_config import get_logger
from app.repository.user_repository import UserRepository
from app.repository.feed_repository import FeedRepository
from app.services.image_service import ImageService
from app.utils.token import get_user_id_from_token
import time, json

logger = get_logger(__name__)


# TODO: 쿼리문을 합칠 수 있는것들 합치거나, 따로 빼서 유틸함수로 정리할 수 있는 부분은 정리하기!
class UserService:
    def __init__(
        self,
        user_repository: UserRepository,
        feed_repository: FeedRepository,
        image_service: ImageService,
    ):
        self.db = db
        self.user_repository = user_repository
        self.image_service = image_service
        self.feed_repository = feed_repository

    # form data는 JSON이 아니다. FastAPI가 Pydantic 모델에 자동으로 변환해주지 않음.
    # 이 데이터 형식은 multipart/form-data가 되는데 Pydantic 모델을 Form 입력값으로 감싸서 생성하는 팩토리 메서드로
    # Depends()로 넘긴 함수의 시그니처를 보고 의존성 주입.
    # TODO: 최적화 필요: 여기 추가할 수 있나?
    async def create_user(
        self,
        user_form: UserCreateRequest,
        profile_images: List[UploadFile],
        secret_images: Optional[List[UploadFile]] = None,
    ) -> bool:
        hashtags = Hashtags.parse_raw(user_form.hashtags)
        try:
            user_data = (
                user_form.id,
                user_form.fcm,
                user_form.sns,
                user_form.name,
                user_form.phone,
                user_form.provider,
                user_form.email,
                user_form.nickname,
                user_form.birthday,
                user_form.age,
                user_form.height,
                user_form.weight,
                user_form.country,
                user_form.position,
                user_form.relation,
                hashtags.json(),
                user_form.self_introduction,
                user_form.bdsm_type,
                user_form.marketing_agree,
                user_form.service_agree,
                user_form.personal_agree,
                user_form.personal_chat_alarm,
                user_form.group_chat_alarm,
                user_form.post_comment_alarm,
                user_form.post_like_alarm,
                user_form.night_agree,
                user_form.leave,
                user_form.test or "",
                user_form.auth,
            )

            await self.user_repository.insert_user(user_data)

            profile_urls = await self.image_service.upload_images(
                user_id=user_form.id,
                images=profile_images,
                image_label="user_profile",
            )
            await self.user_repository.insert_user_images(
                user_form.id, profile_urls, start_index=0
            )

            secret_urls = await self.image_service.upload_images(
                user_id=user_form.id,
                images=secret_images,
                image_label="user_secret_profile",
            )
            if secret_urls:
                await self.user_repository.insert_secret_images(
                    user_form.id, secret_urls
                )

            user_row, columns = await self.user_repository.get_user_row(user_form.id)
            if user_row and columns:
                await self.user_repository.insert_user_history(user_row, columns)
            logger.info(f"유저 생성을 완료했습니다. user_id: {user_form.id}")
            return True
        except Exception as e:
            logger.error(f"유저 생성을 실패했습니다: {str(e)}")
            raise HTTPException(status_code=500, detail="사용자 생성 실패")

    async def create_user_endpoint_without_auth(
        self,
        user_form: NoAuthUserCreateRequest,
        profile_images: List[UploadFile],
        secret_images: Optional[List[UploadFile]] = None,
    ) -> bool:
        hashtags = Hashtags.parse_raw(user_form.hashtags)
        try:
            user_data = (
                user_form.id,
                user_form.fcm,
                user_form.sns,
                "",
                "",
                "",
                user_form.email,
                user_form.nickname,
                "",
                user_form.age,
                user_form.height,
                user_form.weight,
                user_form.country,
                user_form.position,
                user_form.relation,
                hashtags.json(),
                user_form.self_introduction,
                user_form.bdsm_type,
                user_form.marketing_agree,
                user_form.service_agree,
                user_form.personal_agree,
                user_form.personal_chat_alarm,
                user_form.group_chat_alarm,
                user_form.post_comment_alarm,
                user_form.post_like_alarm,
                user_form.night_agree,
                user_form.leave,
                user_form.test or "",
                user_form.auth,
            )
            await self.user_repository.insert_user(user_data)
            profile_urls = await self.image_service.upload_images(
                user_id=user_form.id,
                images=profile_images,
                image_label="user_profile",
            )
            await self.user_repository.insert_user_images(
                user_form.id, profile_urls, start_index=0
            )

            secret_urls = await self.image_service.upload_images(
                user_id=user_form.id,
                images=secret_images,
                image_label="user_secret_profile",
            )
            if secret_urls:
                await self.user_repository.insert_secret_images(
                    user_form.id, secret_urls
                )

            user_row, columns = await self.user_repository.get_user_row(user_form.id)
            if user_row and columns:
                await self.user_repository.insert_user_history(user_row, columns)
            logger.info(f"유저 생성을 완료했습니다. user_id: {user_form.id}")
            return True
        except Exception as e:
            logger.error(f"유저 생성을 실패했습니다: {str(e)}")
            raise HTTPException(status_code=500, detail="사용자 생성 실패")

    # TODO: 최적화 필요
    async def fetch_my_profile(self, user_id: str) -> UserProfileResponse | None:
        try:
            row = await self.user_repository.fetch_my_profile(user_id)
            if not row:
                raise HTTPException(
                    status_code=404, detail="존재하지 않는 사용자입니다."
                )

            # JSON 필드 파싱
            profile_images = json.loads(row.profileImages) if row.profileImages else []
            secret_images = json.loads(row.secretImages) if row.secretImages else []
            block_user_list = json.loads(row.blockUserList) if row.blockUserList else []
            favorite_list = (
                json.loads(row.favoriteUserList) if row.favoriteUserList else []
            )
            following_list = json.loads(row.followingList) if row.followingList else []
            use_coupon_list = json.loads(row.useCouponList) if row.useCouponList else []

            return UserProfileResponse(
                id=row.id,
                nickname=row.nickname,
                birthday=row.birthday,
                age=row.age,
                height=row.height,
                weight=row.weight,
                sns=row.sns,
                relation=row.relation,
                provider=row.provider,
                position=row.position,
                country=row.country,
                hashtags=Hashtags.parse_raw(row.hashtags),
                selfIntroduction=row.self_introduction,
                bdsmType=row.bdsm_type,
                talkStyle=row.talk_style,
                profileImages=profile_images,
                secretYn=row.secret_yn,
                credit=row.credit,
                todayAdCount=row.todayAdCount,
                secretImages=secret_images,
                marketingAlarm=row.marketing_agree,
                nightAlarm=row.night_agree,
                personalChatAlarm=row.personal_chat_alarm_agree,
                groupChatAlarm=row.group_chat_alarm_agree,
                postCommentAlarm=row.post_comment_alarm_agree,
                postLikeAlarm=row.post_like_alarm_agree,
                profileAlarm=row.profile_alarm_agree,
                secretAlarm=row.secret_alarm_agree,
                feedLikeAlarm=row.feed_like_alarm_agree,
                feedCommentAlarm=row.feed_comment_alarm_agree,
                followAlarm=row.follow_alarm_agree,
                pushRead=row.pushRead,
                profileRead=row.profileRead,
                banned=row.banned,
                unBannedDate=row.unbanned_dt,
                auth=row.auth_yn,
                blockUserList=block_user_list,
                blockPostList=[],
                blockCommentList=[],
                favoriteUserList=favorite_list,
                lastConnectedAt=row.last_connected_at,
                latitude=row.latitude,
                longitude=row.longitude,
                hasSecretFeed=row.hasSecretFeed,
                followerCount=row.followerCount,
                followingCount=row.followingCount,
                followingList=following_list,
                useCouponList=use_coupon_list,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"내 정보 조회 실패: {str(e)}")
            raise HTTPException(status_code=500, detail=f"내 정보 조회 실패: {str(e)}")

    async def verify_user(
        self,
        token: str,
        name: str,
        phone: str,
        birthday: str,
        provider: str,
    ):
        user_id = await get_user_id_from_token(token)
        await self.user_repository.verify_user(
            user_id=user_id,
            name=name,
            phone=phone,
            birthday=birthday,
            provider=provider,
        )

    async def check_nickname(self, nickname: str) -> bool:
        return await self.user_repository.check_nickname(nickname)

    async def update_user_nickname(self, id: str, nickname: str) -> str:
        user = await self.user_repository.fetch_active_user(id)
        if not user:
            logger.error(f"존재하지 않는 사용자입니다. user_id: {id}")
            return "not_found"

        if await self.user_repository.check_nickname(nickname):
            logger.error(f"중복된 닉네임입니다. nickname: {nickname}")
            return "duplicate"

        await self.user_repository.update_user_nickname(id, nickname)

        user_row, columns = await self.user_repository.get_user_row(id)
        if user_row and columns:
            await self.user_repository.insert_user_history(user_row, columns)

        return "success"

    async def update_user_hashtag(self, id: str, hashtags: Hashtags) -> bool:
        user = await self.user_repository.fetch_active_user(id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await self.user_repository.update_user_hashtags(id, hashtags.json())
        user_row, columns = await self.user_repository.get_user_row(id)
        if user_row and columns:
            await self.user_repository.insert_user_history(user_row, columns)

        return True

    async def update_user_info(
        self, id: str, age: int, height: int, weight: int, country: str
    ) -> bool:
        user = await self.user_repository.fetch_active_user(id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await self.user_repository.update_user_info(id, age, height, weight, country)

        user_row, columns = await self.user_repository.get_user_row(id)
        if user_row and columns:
            await self.user_repository.insert_user_history(user_row, columns)

        return True

    async def update_user_fcm(self, id: str, fcm: str) -> bool:
        user = await self.user_repository.fetch_active_user(id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await self.user_repository.update_user_fcm(id, fcm)

        user_row, columns = await self.user_repository.get_user_row(id)
        if user_row and columns:
            await self.user_repository.insert_user_history(user_row, columns)

        return True

    async def update_user_relation(self, id: str, relation: str) -> bool:
        user = await self.user_repository.fetch_active_user(id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await self.user_repository.update_user_relation(id, relation)

        user_row, columns = await self.user_repository.get_user_row(id)
        if user_row and columns:
            await self.user_repository.insert_user_history(user_row, columns)
        return True

    async def update_user_position(self, id: str, position: str) -> bool:
        user = await self.user_repository.fetch_active_user(id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await self.user_repository.update_user_position(id, position)

        user_row, columns = await self.user_repository.get_user_row(id)
        if user_row and columns:
            await self.user_repository.insert_user_history(user_row, columns)
        return True

    async def update_user_talk_style(self, id: str, talk_style: str) -> bool:
        user = await self.user_repository.fetch_active_user(id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await self.user_repository.update_user_talk_style(id, talk_style)

        user_row, columns = await self.user_repository.get_user_row(id)
        if user_row and columns:
            await self.user_repository.insert_user_history(user_row, columns)
        return True

    async def update_user_alarm(self, id: str, type: str, value: bool) -> bool:
        user = await self.user_repository.fetch_active_user(id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await self.user_repository.update_user_alarm(id, type, value)

        user_row, columns = await self.user_repository.get_user_row(id)
        if user_row and columns:
            await self.user_repository.insert_user_history(user_row, columns)
        return True

    async def update_user_self_introduction(
        self, id: str, user_self_introduction: str
    ) -> bool:
        user = await self.user_repository.fetch_active_user(id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await self.user_repository.update_user_self_introduction(
            id, user_self_introduction
        )

        user_row, columns = await self.user_repository.get_user_row(id)
        if user_row and columns:
            await self.user_repository.insert_user_history(user_row, columns)
        return True

    async def update_user_bdsm_type(self, user_id: str, bdsm_type: str) -> bool:
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await self.user_repository.update_user_bdsm_type(user_id, bdsm_type)
        user_row, columns = await self.user_repository.get_user_row(user_id)
        if user_row and columns:
            await self.user_repository.insert_user_history(user_row, columns)
        return True

    async def check_user_block(self, user_id: str, target_user_id: str) -> bool:
        return await self.user_repository.check_user_block(user_id, target_user_id)

    async def fetch_user_profile(self, user_id: str, viewer_id: Optional[str]):
        try:
            row = await self.user_repository.fetch_user_profile(user_id)
            if not row:
                return {}

            # JSON → Python list
            profile_images = json.loads(row.profileImages) if row.profileImages else []
            secret_images = json.loads(row.secretImages) if row.secretImages else []
            block_user_list = json.loads(row.blockUserList) if row.blockUserList else []

            # viewer 관련
            if viewer_id is None:
                is_blocked = False
                today_view_count = 0
                total_view_count = 0
            else:
                is_blocked = await self.check_user_block(user_id, viewer_id)
                today_view_count = await self.user_repository.fetch_today_view_count(
                    user_id, viewer_id
                )
                total_view_count = await self.user_repository.fetch_total_view_count(
                    user_id, viewer_id
                )

            return UserDetailResponse(
                id=row.id,
                fcm=row.fcm,
                nickname=row.nickname,
                birthday=row.birthday,
                relation=row.relation,
                position=row.position,
                country=row.country,
                age=row.age,
                height=row.height,
                weight=row.weight,
                hashtags=Hashtags.parse_raw(row.hashtags),
                selfIntroduction=row.self_introduction,
                bdsmType=row.bdsm_type,
                talkStyle=row.talk_style,
                secretYn=row.secret_yn,
                profileImages=profile_images,
                secretImages=secret_images if row.secret_yn else [],
                auth=row.auth_yn,
                leaved=row.leaved,
                personalChatAlarm=row.personal_chat_alarm_agree,
                groupChatAlarm=row.group_chat_alarm_agree,
                postCommentAlarm=row.post_comment_alarm_agree,
                postLikeAlarm=row.post_like_alarm_agree,
                blockUserList=block_user_list,
                lastConnectedAt=row.last_connected_at,
                latitude=row.latitude,
                longitude=row.longitude,
                isBlocked=is_blocked,
                todayViewCount=today_view_count,
                totalViewCount=total_view_count,
                followerCount=row.followerCount,
                followingCount=row.followingCount,
            )
        except Exception as e:
            logger.error(f"유저 정보 조회 실패: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"유저 정보 조회 실패: {str(e)}"
            )

    async def block_user(self, id: str, user_id: str) -> bool:
        active_user = await self.user_repository.fetch_active_user(id)
        if not active_user:
            logger.error(f"존재하지 않는 사용자입니다. user_id: {id}")
            raise HTTPException(status_code=404, detail="User not found")

        target_user = await self.user_repository.fetch_active_user(user_id)
        if not target_user:
            logger.error(f"차단할 사용자가 존재하지 않습니다. user_id: {user_id}")
            raise HTTPException(status_code=404, detail="Blocked user not found")

        await self.user_repository.block_user(id, user_id)
        return True

    async def report_user(
        self, chatId: str, reportUserId: str, reportedUserId: str, reason: str
    ) -> bool:
        reporter = await self.user_repository.fetch_active_user(reportUserId)
        if not reporter:
            logger.error(f"신고한 사용자가 존재하지 않습니다. user_id: {reportUserId}")
            raise HTTPException(status_code=404, detail="Reporting user not found")

        reported = await self.user_repository.fetch_active_user(reportedUserId)
        if not reported:
            logger.error(
                f"신고당한 사용자가 존재하지 않습니다. user_id: {reportedUserId}"
            )
            raise HTTPException(status_code=404, detail="Reported user not found")

        await self.user_repository.report_user(
            chatId, reportUserId, reportedUserId, reason
        )
        return True

    async def fetch_user_list(
        self, user_id: str, user_id_list: List[str]
    ) -> List[UserListResponse]:
        if not user_id_list:
            return []
        user_rows = await self.user_repository.fetch_user_list(user_id_list, user_id)

        user_profiles: List[UserListResponse] = []
        for user_row in user_rows:
            user_profiles.append(
                UserListResponse(
                    id=user_row.id,
                    fcm=user_row.fcm,
                    nickname=user_row.nickname,
                    birthday=user_row.birthday,
                    age=user_row.age,
                    height=user_row.height,
                    weight=user_row.weight,
                    relation=user_row.relation,
                    position=user_row.position,
                    country=user_row.country,
                    hashtags=Hashtags.parse_raw(user_row.hashtags),
                    selfIntroduction=user_row.self_introduction,
                    bdsmType=user_row.bdsm_type,
                    talkStyle=user_row.talk_style,
                    secretYn=user_row.secret_yn,
                    auth=user_row.auth_yn,
                    secretImages=user_row.secretImages,
                    profileImages=user_row.profileImages,
                    leaved=user_row.leaved,
                    personalChatAlarm=user_row.personal_chat_alarm_agree,
                    groupChatAlarm=user_row.group_chat_alarm_agree,
                    postCommentAlarm=user_row.post_comment_alarm_agree,
                    postLikeAlarm=user_row.post_like_alarm_agree,
                    blockUserList=user_row.blockUserList,
                    lastConnectedAt=user_row.last_connected_at,
                    isBlocked=user_row.isBlocked,
                    latitude=user_row.latitude,
                    longitude=user_row.longitude,
                    followerCount=user_row.followerCount,
                    followingCount=user_row.followingCount,
                )
            )
        return user_profiles

    async def fetch_user_id_list(
        self,
        user_id: str,
        position: str,
        relation: str,
        bdsm_type: str,
        talk_style: str,
        age: str,
        secret: bool,
    ) -> List[str]:
        return await self.user_repository.fetch_user_id_list(
            user_id=user_id,
            position=position,
            relation=relation,
            bdsm_type=bdsm_type,
            talk_style=talk_style,
            age=age,
            secret=secret,
        )

    async def fetch_near_user_id_list(
        self,
        user_id: str,
        position: str,
        relation: str,
        bdsm_type: str,
        talk_style: str,
        secret: bool,
        age: str,
    ) -> List[str]:
        return await self.user_repository.fetch_near_user_id_list(
            user_id=user_id,
            position=position,
            relation=relation,
            bdsm_type=bdsm_type,
            talk_style=talk_style,
            age=age,
            secret=secret,
        )

    async def fetch_nearby_user_list(
        self,
        token: str,
        page: int,
        age: str,
        position: str,
        relation: str,
        bdsm_type: str,
        talk_style: str,
        secret: bool,
    ) -> List[UserListResponse]:

        # 응답 시간 로깅을 위한
        user_id = await get_user_id_from_token(token)
        user_list = await self.user_repository.fetch_nearby_user_list(
            user_id=user_id,
            page=page,
            age=age,
            position=position,
            relation=relation,
            bdsm_type=bdsm_type,
            talk_style=talk_style,
            secret=secret,
        )
        user_profiles = await self.fetch_user_list(
            user_id=user_id, user_id_list=user_list
        )

        return user_profiles

    async def fetch_user_fcm_list(self, user_id_list: List[str]) -> List[str]:
        if not user_id_list:
            return []

        return await self.user_repository.fetch_user_fcm_list(user_id_list)

    async def leave_user(self, user_id: str, reason: str) -> bool:
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await self.user_repository.leave_user(user_id, reason)

        user_row, columns = await self.user_repository.get_user_row(user_id)
        if user_row and columns:
            await self.user_repository.insert_user_history(user_row, columns)

        return True

    async def user_health_check(
        self,
        user_id: str,
        user_latitude: Optional[float],
        user_longitude: Optional[float],
    ) -> bool:
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

        await self.user_repository.user_health_check(
            user_id, user_latitude, user_longitude
        )
        return True

    async def update_user_images(
        self,
        user_id: str,
        image_index: Optional[List[str]] = None,
        image: Optional[List[UploadFile]] = None,
    ):
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

        # 현재 이미지 목록 조회
        origin_images = await self.user_repository.fetch_profile_images(user_id)

        # 이미지 정리
        if image_index:
            if len(image_index) == 1 and "," in image_index[0]:
                image_index = image_index[0].split(",")
        else:
            image_index = []
        image_index = [url.strip() for url in image_index]

        keep_images = [url for url in image_index if url in origin_images]
        remove_images = [url for url in origin_images if url not in image_index]

        uploaded_urls = []
        if image:
            start_index = len(keep_images)
            for idx, file in enumerate(image):
                now = datetime.now().strftime("%Y%m%d_%H%M%S%f")[:-3]
                ext = file.filename.split(".")[-1] or "jpg"
                filename = f"{now}.{ext}"
                s3_key = f"user_profile/{user_id}/"

                file.file.seek(0)
                if not upload_file_to_s3(file.file, s3_key, filename):
                    raise HTTPException(
                        status_code=500, detail=f"S3 업로드 실패: {file.filename}"
                    )

                image_url = f"{CLOUDFRONT_URL}/{s3_key}{filename}"
                uploaded_urls.append(image_url)

        all_images = await self.user_repository.update_user_images(
            user_id=user_id,
            keep_images=keep_images,
            remove_images=remove_images,
            uploaded_urls=uploaded_urls,
        )

        return all_images

    async def fetch_user_push_list(
        self, push_type: Optional[str], page: int, user_id: str
    ) -> List[dict]:
        user_no = await self.user_repository.fetch_user_no(user_id)
        if not user_no:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

        push_rows = await self.user_repository.fetch_push_user_logs(
            user_no=user_no, push_type=push_type, page=page
        )

        push_list = [
            {
                "token": row[0],
                "payload": row[1],
                "deliveredAt": row[2],
                "openedAt": row[3],
            }
            for row in push_rows
        ]

        return push_list

    async def receive_user_push(self, push_id: str, user_id: str) -> bool:
        user_no = await self.user_repository.fetch_user_no(user_id)
        if not user_no:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

        updated = await self.user_repository.update_push_opened_state(user_no, push_id)
        if not updated:
            raise HTTPException(status_code=404, detail="푸시 로그를 찾을 수 없습니다.")

        return True

    async def receive_all_user_push(self, user_id: str) -> bool:
        user_no = await self.user_repository.fetch_user_no(user_id)
        if not user_no:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

        updated = await self.user_repository.update_all_push_opened_state(user_no)
        if not updated:
            raise HTTPException(status_code=404, detail="읽을 푸시 로그가 없습니다.")

        return True

    async def insert_user_profile_view(self, user_id: str, viewer_id: str) -> bool:
        is_active = await self.user_repository.fetch_active_user(user_id)
        if not is_active:
            raise HTTPException(status_code=404, detail="존재하지 않는 사용자입니다.")

        is_viewer_active = await self.user_repository.fetch_active_user(viewer_id)
        if not is_viewer_active:
            raise HTTPException(status_code=404, detail="존재하지 않는 조회자입니다.")

        try:
            await self.user_repository.insert_user_profile_view(user_id, viewer_id)
            return True

        except Exception:
            raise HTTPException(status_code=500, detail="프로필 조회 로그 저장 실패")

    # 상대가 나를 차단했어도 안보이게(놔두도록 한다. 상대방의 행동이 나에게 오지만 않으면 될것).
    async def fetch_user_profile_view(self, page: int, user_id: str) -> list[dict]:
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

        try:
            view_list = await self.user_repository.fetch_user_profile_view(
                page, user_id
            )
            user_no = await self.user_repository.fetch_user_no(user_id)
            if user_no:
                await self.user_repository.mark_profile_push_read(user_no)

            return view_list

        except Exception as e:
            raise HTTPException(
                status_code=500, detail="프로필 조회 목록 조회 실패, " + str(e)
            )

    async def insert_user_secret_images_view(
        self, user_id: str, target_user_id: str
    ) -> bool:
        is_active = await self.user_repository.fetch_active_user(user_id)
        if not is_active:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

        is_target_active = await self.user_repository.fetch_active_user(target_user_id)
        if not is_target_active:
            raise HTTPException(
                status_code=404, detail="존재하지 않는 상대 유저입니다."
            )

        try:
            await self.user_repository.insert_user_secret_images_view(
                user_id, target_user_id
            )
            return True

        except Exception:
            raise HTTPException(
                status_code=500, detail="시크릿 이미지 열람 기록 저장 실패"
            )

    # TODO : 프로필 카운트로 선회.
    async def fetch_user_secret_list(self, user_id: str, page: int) -> list[dict]:
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

        try:
            secret_list = await self.user_repository.fetch_user_secret_list(
                page, user_id
            )
            user_no = await self.user_repository.fetch_user_no(user_id)
            if user_no:
                await self.user_repository.mark_secret_push_as_read(user_no)

            return secret_list

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"시크릿 앨범 조회 목록 조회 실패. str{e}"
            )

    async def fetch_user_secret_images(self, user_id: str, target_user_id: str) -> bool:
        is_target_active = await self.user_repository.fetch_active_user(target_user_id)
        if not is_target_active:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

        has_target_secret = await self.user_repository.has_secret_images(target_user_id)
        if not has_target_secret:
            raise HTTPException(
                status_code=404, detail="상대방의 시크릿 앨범이 존재하지 않습니다."
            )

        has_my_secret = await self.user_repository.has_secret_images(user_id)
        if not has_my_secret:
            raise HTTPException(
                status_code=404, detail="본인의 시크릿 앨범이 존재하지 않습니다."
            )

        already_requested = await self.user_repository.has_pending_secret_request(
            target_user_id, user_id
        )
        if already_requested:
            raise HTTPException(status_code=400, detail="이미 요청한 상태입니다.")
        try:
            await self.user_repository.insert_secret_request(target_user_id, user_id)
            return True

        except Exception:
            raise HTTPException(status_code=500, detail="시크릿 앨범 요청 저장 실패")

    async def insert_user_credit_secret_list(
        self, user_id: str, secret_user_id: str
    ) -> bool:
        secret_yn = await self.user_repository.fetch_secret_album_status(secret_user_id)
        if not secret_yn:
            raise HTTPException(
                status_code=404, detail="상대방의 시크릿 앨범이 존재하지 않습니다."
            )
        try:
            await self.user_repository.insert_user_credit_secret_view(
                user_id, secret_user_id
            )
            return True

        except Exception:
            raise HTTPException(
                status_code=500, detail="시크릿 앨범 열람 기록 저장 실패"
            )

    async def fetch_user_credit_secret_view(
        self, page: int, user_id: str
    ) -> list[dict]:
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

        try:
            credit_secret_list = (
                await self.user_repository.fetch_credit_secret_view_list(page, user_id)
            )
            return credit_secret_list

        except Exception as e:
            logger.error(f"시크릿 열람 내역 조회 실패: {str(e)}")
            raise HTTPException(status_code=500, detail="시크릿 열람 내역 조회 실패")

    async def accept_user_secret_images(
        self, user_id: str, target_user_id: str
    ) -> bool:
        user = await self.user_repository.fetch_active_user(target_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

        try:
            exists = await self.user_repository.has_pending_secret_request(
                target_user_id, user_id
            )
            if not exists:
                raise HTTPException(status_code=400, detail="요청이 존재하지 않습니다.")

            await self.user_repository.approve_secret_request(target_user_id, user_id)
            return True

        except Exception:
            raise HTTPException(status_code=500, detail="시크릿 앨범 승인 처리 실패")

    async def reject_user_secret_images(
        self, user_id: str, target_user_id: str
    ) -> bool:
        user = await self.user_repository.fetch_active_user(target_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

        try:
            exists = await self.user_repository.has_pending_secret_request(
                target_user_id, user_id
            )
            if not exists:
                raise HTTPException(status_code=400, detail="요청이 존재하지 않습니다.")

            await self.user_repository.reject_secret_request(target_user_id, user_id)
            return True

        except Exception:
            raise HTTPException(status_code=500, detail="시크릿 앨범 거절 처리 실패")

    async def fetch_my_secret_requests(self, user_id: str) -> list[UserSecretResponse]:
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

        try:
            requests = await self.user_repository.fetch_my_secret_requests(user_id)
            return requests
        except Exception:
            raise HTTPException(status_code=500, detail="내 시크릿 요청 목록 조회 실패")

    async def fetch_opponent_secret_requests(
        self, user_id: str
    ) -> list[UserSecretResponse]:
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

        try:
            requests = await self.user_repository.fetch_opponent_secret_requests(
                user_id
            )
            return requests
        except Exception:
            raise HTTPException(
                status_code=500, detail="상대 시크릿 요청 목록 조회 실패"
            )

    async def cancel_my_secret_request(self, user_id: str, target_user_id: str) -> bool:
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

        try:
            exists = await self.user_repository.has_pending_secret_request(
                target_user_id, user_id
            )
            if not exists:
                raise HTTPException(status_code=400, detail="요청이 존재하지 않습니다.")

            await self.user_repository.cancel_secret_request(target_user_id, user_id)
            return True
        except Exception:
            raise HTTPException(status_code=500, detail="시크릿 요청 취소 실패")

    async def fetch_my_secret_images(self, user_id: str) -> list[str] | None:
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

        try:
            return await self.user_repository.fetch_my_secret_images(user_id)
        except Exception:
            raise HTTPException(status_code=500, detail="시크릿 앨범 조회 실패")

    async def cancel_accept_my_secret_request(
        self, user_id: str, target_user_id: str
    ) -> bool:
        target = await self.user_repository.fetch_active_user(target_user_id)
        if not target:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

        try:
            exists = await self.user_repository.has_approved_secret_request(
                user_id, target_user_id
            )
            if not exists:
                raise HTTPException(status_code=400, detail="요청이 존재하지 않습니다.")

            await self.user_repository.cancel_approved_secret_request(
                user_id, target_user_id
            )
            return True

        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=500, detail="시크릿 요청 승인 취소 실패")

    async def fetch_accepted_secret_images(
        self, user_id: str, target_user_id: str
    ) -> list[str] | None:
        target = await self.user_repository.fetch_active_user(target_user_id)
        if not target:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

        try:
            # 승인 상태 확인
            is_approved = await self.user_repository.has_approved_secret_request(
                target_user_id, user_id
            )
            if not is_approved:
                raise HTTPException(
                    status_code=400, detail="요청이 승인되지 않았습니다."
                )

            # 승인된 시크릿 이미지 가져오기
            return await self.user_repository.fetch_secret_images(target_user_id)

        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=500, detail="승인된 시크릿 앨범 조회 실패")

    async def give_user_credit(self, user_id: str, type: str) -> int:
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

        type_map = {
            "history_reward": (1, "광고 시청 보상"),
        }

        if type not in type_map:
            raise HTTPException(
                status_code=400, detail="고래 코인 타입이 올바르지 않습니다."
            )

        try:
            credit, reason = type_map[type]
            await self.user_repository.add_user_credit(user_id, credit, reason)
            return credit

        except Exception:
            raise HTTPException(status_code=500, detail="고래 코인 지급 실패")

    async def consume_user_credit(self, user_id: str, type: str) -> int:
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

        type_map = {
            "history_view": (1, "프로필 조회"),
            "secret_view": (5, "시크릿 앨범 조회"),
            "bypass_secret_view": (10, "우회한 시크릿 앨범 조회"),
        }

        if type not in type_map:
            raise HTTPException(
                status_code=400, detail="고래 코인 타입이 올바르지 않습니다."
            )

        try:
            credit, reason = type_map[type]
            current_credit = await self.user_repository.fetch_user_credit(user_id)
            if current_credit < credit:
                raise HTTPException(status_code=400, detail="고래 코인이 부족합니다.")
            await self.user_repository.deduct_user_credit(user_id, credit, reason)
            return credit

        except Exception:
            raise HTTPException(status_code=500, detail="고래 코인 차감 실패")

    async def add_user_credit_profile_view(
        self, viewer_id: str, viewed_id: str, credit_type: Optional[str] = None
    ) -> bool:
        viewer = await self.user_repository.fetch_active_user(viewer_id)
        if not viewer:
            raise HTTPException(status_code=404, detail="존재하지 않는 사용자입니다.")

        target = await self.user_repository.fetch_active_user(viewed_id)
        if not target:
            raise HTTPException(status_code=404, detail="상대방을 찾을 수 없습니다.")

        try:
            if credit_type == None:
                await self.user_repository.insert_credit_profile_view(
                    viewer_id, viewed_id
                )
                return True
            elif credit_type == "history_view":
                await self.user_repository.insert_credit_profile_view(
                    viewer_id, viewed_id
                )
                # 유저 크레딧 차감
                await self.consume_user_credit(viewer_id, "history_view")
                return True
            return True
        except Exception:
            raise HTTPException(
                status_code=500, detail="프로필 크레딧 조회 기록 저장 실패"
            )

    async def fetch_user_credit_profile_view(
        self, user_id: str, page: int
    ) -> list[dict]:
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="존재하지 않는 사용자입니다.")

        try:
            view_list = await self.user_repository.fetch_credit_profile_view_list(
                user_id, page
            )
            return view_list
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"크레딧 프로필 조회 목록 조회 실패, str{e}"
            )

    async def fetch_user_block_list(self, user_id: str, page: int) -> list[str]:
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

        try:
            block_list = await self.user_repository.fetch_user_block_list_page(
                user_id, page
            )
            return block_list
        except Exception:
            raise HTTPException(status_code=500, detail="차단 목록 조회 실패")

    async def unblock_user(self, user_id: str, target_user_id: str) -> bool:
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

        opponent = await self.user_repository.fetch_active_user(target_user_id)
        if not opponent:
            raise HTTPException(status_code=404, detail="상대방을 찾을 수 없습니다.")

        try:
            await self.user_repository.delete_block_user(user_id, target_user_id)
            return True
        except Exception:
            raise HTTPException(status_code=500, detail="차단 해제 실패")

    async def poke_user(self, user_id: str, target_user_id: str) -> bool:
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="존재하지 않는 사용자입니다.")

        target_user = await self.user_repository.fetch_active_user(target_user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="존재하지 않는 상대방입니다.")

        try:
            await self.user_repository.poke_user(user_id, target_user_id)
            return True
        except Exception:
            raise HTTPException(status_code=500, detail="찌르기 처리 실패")

    async def fetch_my_poke_list(self, user_id: str, page: int) -> list[dict]:
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

        try:
            poke_list = await self.user_repository.fetch_my_poke_list(user_id, page)
            return poke_list
        except Exception:
            raise HTTPException(status_code=500, detail="찌르기 목록 조회 실패")

    async def favorite_user(self, user_id: str, target_user_id: str) -> bool:
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="존재하지 않는 사용자입니다.")

        target_user = await self.user_repository.fetch_active_user(target_user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="존재하지 않는 상대방입니다.")

        try:
            is_favorited = await self.user_repository.favorite_user(
                user_id, target_user_id
            )
            return is_favorited
        except Exception:
            raise HTTPException(status_code=500, detail="즐겨찾기 처리 실패")

    async def fetch_user_unlock_count(self, user_id: str) -> dict:
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="존재하지 않는 사용자입니다.")

        try:
            return await self.user_repository.fetch_user_unlock_count(user_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"열람 통계 조회 실패, str{e}")

    async def fetch_user_credit_history(
        self, page: int, type: str, token: str
    ) -> UserCreditHistoryResponse:
        user_id = await get_user_id_from_token(token)
        credit_histories = await self.user_repository.fetch_user_credit_history(
            page=page, type=type, user_id=user_id
        )

        credit_history_map = {
            "프로필 조회": {
                "title": "방문 기록",
                "content": "블라인드 프로필 해제",
            },
            "시크릿 앨범 조회": {"title": "시크릿 앨범", "content": "시크릿 앨범 보기"},
            "우회한 시크릿 앨범 조회": {
                "title": "시크릿 앨범",
                "content": "시크릿 앨범 보기",
            },
            "시크릿 피드 구매": {"title": "시크릿 피드", "content": "시크릿 피드 보기"},
            "시크릿 피드 블라인드 프로필 구매": {
                "title": "시크릿 피드",
                "content": "블라인드 프로필 해제",
            },
            "우회한 시크릿 피드 구매": {
                "title": "시크릿 피드",
                "content": "시크릿 피드 보기",
            },
            "고래 구입": {"title": "고래 코인 충전", "content": "고래 코인 충전"},
            "광고 시청 보상": {"title": "광고 시청", "content": "광고 시청 리워드"},
            "회원가입 이벤트 보상": {
                "title": "이벤트",
                "content": "신규 회원가입 보상",
            },
            "3일 이상 미접속 리워드 지급": {
                "title": "이벤트",
                "content": "웰컴백 리워드",
            },
            "시크릿 피드 리베이트 지급": {
                "title": "내 시크릿 피드",
                "content": "시크릿 피드 리베이트",
            },
        }

        credit_history_list: List[UserCreditHistoryResponse] = []
        for credit_history in credit_histories:
            # db에 있는 description값을 꺼내온다
            db_description = credit_history_map.get(credit_history[1])
            if not db_description:
                credit_history_list.append(
                    UserCreditHistoryResponse(
                        amount=credit_history[0],
                        title="",
                        description=credit_history[1],
                        createdAt=credit_history[2],
                    )
                )
                continue

            credit_history_list.append(
                UserCreditHistoryResponse(
                    amount=credit_history[0],
                    title=db_description["title"],
                    description=db_description["content"],
                    createdAt=credit_history[2],
                )
            )
        if not credit_history_list:
            return []
        return credit_history_list

    async def fetch_biz_list(
        self,
        token: str,
        page: int,
    ):
        # 토큰에서 user_id 추출
        user_id = await get_user_id_from_token(token)

        # 비즈 리스트 조회 (레포지토리 호출)
        bizs = await self.user_repository.fetch_biz_list(
            user_id=user_id,
            page=page,
        )

        # 응답 모델 배열 생성
        biz_list: List[BizDetailResponse] = []

        for biz in bizs:
            biz_list.append(
                BizDetailResponse(
                    id=biz[0],
                    bizId=biz[1],
                    storeType=biz[2],
                    storeName=biz[3],
                    email=biz[4],
                    tags=biz[5],
                    address=biz[6],
                    businessHours=biz[7],
                    phone=biz[8],
                    managerPhone=biz[9],
                    latitude=biz[10],
                    longitude=biz[11],
                )
            )

        return biz_list

    # 내가 쿠폰을 사용했는지 여부 표시.
    async def fetch_biz_detail(
        self,
        token: str,
        biz_pk: int,
    ):
        user_id = await get_user_id_from_token(token)

        detail = await self.user_repository.fetch_biz_detail(
            user_id=user_id,
            biz_pk=biz_pk,
        )

        if detail is False:
            raise HTTPException(status_code=404, detail="존재하지 않는 비즈입니다.")

        biz_detail = BizDetailResponse()

    async def create_biz_review(
        self,
        token: str,
        biz_id: str,
        content: str,
        rating: int,
        review_images: Optional[List[UploadFile]] = None,
    ):
        # 토큰에서 user_id 추출
        user_id = await get_user_id_from_token(token)

        # 비즈 리뷰 업로드
        review_id = await self.user_repository.create_biz_review(
            user_id=user_id,
            biz_id=biz_id,
            content=content,
            rating=rating,
        )

        if not review_images:
            return True

        image_urls = await self.image_service.upload_images(
            user_id=biz_id,
            images=review_images,
            image_label="biz_review",
        )

        await self.user_repository.insert_biz_review_images(
            review_id=review_id, user_id=user_id, image_urls=image_urls, start_index=0
        )
        return True

    async def update_biz_review(
        self,
        token: str,
        review_id: int,
        content: str,
        rating: int,
        images: Optional[List[str]] = None,
        review_images: Optional[List[UploadFile]] = None,
    ):
        # 1. 토큰 → userId 추출
        user_id = await get_user_id_from_token(token)

        # 2. 작성자 체크
        is_owner = await self.user_repository.is_owner(
            user_id=user_id, review_id=review_id
        )
        if not is_owner:
            logger.error("리뷰 수정 권한 없음")
            return False

        # 3. 기존 이미지 조회
        origin_images = await self.user_repository.get_review_images(review_id)

        # 4. 이미지 URL 파싱 (리스트 또는 ","로 이어진 문자열 모두 처리)
        if images:
            if len(images) == 1 and "," in images[0]:
                images = images[0].split(",")
        else:
            images = []

        images = [url.strip() for url in images]

        # 유지할 이미지
        keep_images = [url for url in images if url in origin_images]

        # 삭제될 이미지
        remove_images = [url for url in origin_images if url not in keep_images]

        # 5. 새 이미지 업로드
        uploaded_urls = []
        if review_images and len(review_images) > 0:
            s3_prefix = f"biz_review/{review_id}/"
            for image in review_images:
                filename = generate_filename(image.filename)
                upload_file_to_s3(image.file, s3_prefix, filename)
                uploaded_urls.append(f"{CLOUDFRONT_URL}/{s3_prefix}{filename}")

        # 6. 이미지 업데이트
        await self.user_repository.update_review_images(
            review_id=review_id,
            user_id=user_id,
            keep_images=keep_images,
            remove_images=remove_images,
            uploaded_urls=uploaded_urls,
        )

        # 7. 리뷰 내용 + 평점 업데이트
        await self.user_repository.update_biz_review(
            review_id=review_id,
            content=content,
            rating=rating,
        )

        return True

    async def delete_biz_review(
        self,
        token: str,
        review_id: str,
    ):
        user_id = await get_user_id_from_token(token)

        result = await self.user_repository.delete_biz_review(
            user_id=user_id,
            review_id=review_id,
        )

        if result is False:
            logger.error(
                f"존재하지 않는 리뷰이거나 삭제 권한이 없습니다. review_id: {review_id}"
            )
            raise HTTPException(status_code=404, detail="리뷰를 삭제할 수 없습니다.")

        return True

    async def block_biz_review(
        self,
        token: str,
        review_id: int,
    ):
        user_id = await get_user_id_from_token(token)

        result = await self.user_repository.block_biz_review(
            user_id=user_id,
            review_id=review_id,
        )
        return True

    async def report_biz_review(
        self,
        token: str,
        review_id: str,
        reason: str,
    ):
        user_id = await get_user_id_from_token(token)

        result = await self.user_repository.report_biz_review(
            user_id=user_id,
            review_id=review_id,
            reason=reason,
        )
        return True

    async def fetch_biz_review_list(
        self,
        token: str,
        biz_id: str,
    ):
        user_id = await get_user_id_from_token(token)

        reviews = await self.user_repository.fetch_biz_review_list(
            user_id=user_id,
            biz_id=biz_id,
        )
        review_list: List[BizReviewResponse] = []
        for review in reviews:
            review_list.append(
                BizReviewResponse(
                    id=review.id,
                    userId=review.user_id,
                    userNickname=review.nickname,
                    bizId=review.biz_id,
                    content=review.content,
                    images=review.images,
                    rating=review.rating,
                    createdAt=review.created_at,
                    answer=(
                        {
                            "content": review.answer_content,
                            "createdAt": review.answer_created_at,
                        }
                    ),
                )
            )
        return review_list

    async def follow_user(
        self,
        token: str,
        follow_id: str,
    ):
        # 토큰에서 user_id 추출
        user_id = await get_user_id_from_token(token)

        # 비즈 팔로우 처리 follower = 팔로우 하는 사람, follow = 팔로우 당하는 사람
        # 팔로우 취소는 False 리턴, 팔로우는 True 리턴
        return await self.user_repository.follow_user(
            follower_id=user_id, follow_id=follow_id
        )

    async def fetch_follow_list(self, user_id: str):

        follow_list = await self.user_repository.fetch_follow_list(user_id=user_id)
        return follow_list

    async def fetch_follower_list(self, user_id: str):

        follower_list = await self.user_repository.fetch_follower_list(user_id=user_id)
        return follower_list

    async def insert_refferal_code(
        self,
        token: str,
        refferal_code: str,
    ):
        # 토큰에서 user_id 추출
        user_id = await get_user_id_from_token(token)

        # 리퍼럴 코드 업데이트
        refferal = await self.user_repository.insert_refferal_code(
            user_id=user_id, refferal_code=refferal_code
        )
        if refferal is False:
            logger.error(f"이미 추천인 코드를 등록한 사용자입니다. user_id: {user_id}")
            raise HTTPException(
                status_code=400, detail="이미 추천인 코드를 등록하였습니다."
            )
        return True

    async def use_biz_coupon(
        self,
        token: str,
        coupon_id: str,
    ):
        user_id = await get_user_id_from_token(token)

        result = await self.user_repository.use_biz_coupon(
            user_id=user_id,
            coupon_id=coupon_id,
        )
        if result == "none":
            logger.error(f"존재하지 않는 쿠폰입니다. coupon_id: {coupon_id}")
            raise HTTPException(status_code=404, detail="존재하지 않는 쿠폰입니다.")
        elif result == "used":
            logger.error(f"이미 사용한 쿠폰입니다. coupon_id: {coupon_id}")
            raise HTTPException(status_code=400, detail="이미 사용한 쿠폰입니다.")
        elif result == "expired":
            logger.error(f"만료된 쿠폰입니다. coupon_id: {coupon_id}")
            raise HTTPException(status_code=400, detail="만료된 쿠폰입니다.")
        elif result == "amount":
            logger.error(f"잔여 쿠폰 수량이 없습니다. coupon_id: {coupon_id}")
            raise HTTPException(status_code=400, detail="잔여 쿠폰 수량이 없습니다.")
        else:
            return True

    async def fetch_user_nickname(
        self,
        user_id: str,
    ):
        nickname = await self.user_repository.fetch_user_nickname(user_id=user_id)
        if not nickname:
            raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")
        return nickname

    async def fetch_biz_owner_id(self, biz_id: str):
        owner_id = await self.user_repository.fetch_biz_owner_id(biz_id=biz_id)
        if not owner_id:
            raise HTTPException(status_code=404, detail="존재하지 않는 비즈입니다.")
        return owner_id
