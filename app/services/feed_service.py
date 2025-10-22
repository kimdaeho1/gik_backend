from typing import Optional, List
from fastapi import HTTPException, status, UploadFile, File
from datetime import datetime
from app.utils.s3_upload import (
    upload_file_to_s3,
    generate_filename,
    image_url_list,
    CLOUDFRONT_URL,
)
from app.db.feed import (
    FeedDetailResponse,
)
from app.utils.token import get_user_id_from_token
from app.utils.logging_config import get_logger
import uuid

logger = get_logger(__name__)


class FeedService:
    def __init__(self, feed_repository):
        self.feed_repository = feed_repository

    async def create_feed(
        self,
        token: str,
        content: Optional[str],
        status: bool,
        secret_status: bool,
        feed_images: Optional[List[UploadFile]] = File(default=[]),
    ):
        # 토큰에서 user_id를 가져오기.
        user_id = await get_user_id_from_token(token)

        # 피드 생성, feed_id는 uuid로 생성.
        feed_id = str(uuid.uuid4())

        image_urls = []
        if feed_images and len(feed_images) > 0:
            s3_prefix = f"feed/{feed_id}/"
            for image in feed_images:
                filename = generate_filename(image.filename)
                success = upload_file_to_s3(image.file, s3_prefix, filename)
                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"이미지 업로드 실패: {image.filename}",
                    )
                image_urls.append(f"{CLOUDFRONT_URL}/{s3_prefix}{filename}")

        if image_urls:
            await self.feed_repository.insert_feed_images(feed_id, user_id, image_urls)
        await self.feed_repository.create_feed(
            feed_id,
            user_id,
            status,
            secret_status,
            content,
        )

        return True

    async def update_feed(
        self,
        token: str,
        feed_id: str,
        content: Optional[str],
        image_urls: Optional[List[str]],
        status: bool,
        secret_status: bool,
        feed_images: Optional[List[UploadFile]] = File(default=[]),
    ):
        user_id = await get_user_id_from_token(token)

        is_owner = await self.feed_repository.is_owner(user_id, feed_id)
        if not is_owner:
            logger.error("피드 수정 권한이 없습니다.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="피드 수정권한이 없습니다.",
            )

        # 현재 이미지 목록 조회
        origin_images = await self.feed_repository.get_feed_images(feed_id)
        origin_images = [row[0] for row in origin_images]
        # 이미지 URL 파싱
        if image_urls:
            if len(image_urls) == 1 and "," in image_urls[0]:
                image_urls = image_urls[0].split(",")
        else:
            image_urls = []

        # 파싱된 이미지들을 리스트로 만들기
        image_urls = [url.strip() for url in image_urls]

        # 지우지 않고 유지할 이미지의 리스트
        keep_images = [url for url in image_urls if url in origin_images]

        # 지울 이미지의 리스트
        remove_images = [url for url in origin_images if url not in keep_images]

        print(keep_images, remove_images)
        # 이미지 업로드
        uploaded_urls = []
        if feed_images and len(feed_images) > 0:
            s3_prefix = f"feed/{feed_id}/"
            for image in feed_images:
                filename = generate_filename(image.filename)
                s3_key = f"{s3_prefix}{filename}"
                upload_file_to_s3(image.file, s3_prefix, filename)
                uploaded_urls.append(f"{CLOUDFRONT_URL}/{s3_key}")

        new_feed_images = await self.feed_repository.update_feed_images(
            feed_id,
            user_id,
            keep_images,
            remove_images,
            uploaded_urls,
        )
        await self.feed_repository.update_feed(
            feed_id,
            status,
            secret_status,
            content,
        )
        return new_feed_images

    async def get_feed(self, token: str, feed_id: str) -> FeedDetailResponse:
        user_id = await get_user_id_from_token(token)

        feed = await self.feed_repository.get_feed(feed_id)
        images = await self.feed_repository.get_feed_images(feed_id)
        like_count = await self.feed_repository.get_feed_like_count(feed_id)
        return FeedDetailResponse(
            feedId=feed[0],
            userId=feed[1],
            content=feed[2],
            images=images,
            status=feed[3],
            secretStatus=feed[4],
            likeCount=like_count,
            createdAt=feed[5],
        )

    async def delete_feed(self, token: str, feed_id: str):
        user_id = await get_user_id_from_token(token)

        is_owner = await self.feed_repository.is_owner(user_id, feed_id)
        if not is_owner:
            logger.error("피드 삭제 권한이 없습니다.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="피드 삭제권한이 없습니다.",
            )

        await self.feed_repository.delete_feed(feed_id)
        return True

    async def report_feed(
        self, token: str, feed_id: str, reported_user_id: str, reason: str
    ):
        user_id = await get_user_id_from_token(token)

        await self.feed_repository.report_feed(
            user_id, feed_id, reported_user_id, reason
        )
        return True

    async def block_feed(self, token: str, feed_id: str):
        user_id = await get_user_id_from_token(token)

        await self.feed_repository.block_feed(user_id, feed_id)
        return True

    async def like_feed(self, token: str, feed_id: str):
        user_id = await get_user_id_from_token(token)

        already_like = await self.feed_repository.exist_like_feed(user_id, feed_id)
        if already_like:
            await self.feed_repository.unlike_feed(user_id, feed_id)
            return "unlike_feed"
        await self.feed_repository.like_feed(user_id, feed_id)
        return "like_feed"

    async def get_my_feed_list(self, token: str, page: int):
        user_id = await get_user_id_from_token(token)
        feeds = await self.feed_repository.get_my_feed_list(user_id, page)

        feed_list: List[FeedDetailResponse] = []
        for feed in feeds:
            images = await self.feed_repository.get_feed_images(feed[0])
            like_count = await self.feed_repository.get_feed_like_count(feed[0])
            feed_list.append(
                FeedDetailResponse(
                    feedId=feed[0],
                    userId=feed[1],
                    content=feed[2],
                    images=images,
                    status=feed[3],
                    secretStatus=feed[4],
                    likeCount=like_count,
                    createdAt=feed[5],
                )
            )
        return feed_list

    # redis 캐싱 추가 예정
    async def get_feed_list(self, token: str, page: int):
        user_id = await get_user_id_from_token(token)
        feeds = await self.feed_repository.get_feed_list(user_id, page)

        feed_list: List[FeedDetailResponse] = []
        for feed in feeds:
            images = await self.feed_repository.get_feed_images(feed[0])
            like_count = await self.feed_repository.get_feed_like_count(feed[0])
            feed_list.append(
                FeedDetailResponse(
                    feedId=feed[0],
                    userId=feed[1],
                    content=feed[2],
                    images=images,
                    status=feed[3],
                    secretStatus=feed[4],
                    likeCount=like_count,
                    createdAt=feed[5],
                )
            )
        return feed_list
