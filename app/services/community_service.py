from fastapi import UploadFile, HTTPException, status
from datetime import datetime
from app.utils.s3_upload import upload_file_to_s3, CLOUDFRONT_URL
from app.utils.s3_upload import generate_filename
from app.utils.utils import kst
from app.db.db_connection import db
from app.db.community import PostListResponse, CommentResponse, PostDetailResponse
from app.repository.community_repository import CommunityRepository
from typing import List, Optional
from sqlalchemy import text
from PIL import Image, ImageFile, ImageOps
import io, uuid, requests
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class CommunityService:
    def __init__(self, db, community_repository: CommunityRepository):
        self.db = db
        self.community_repository = community_repository

    async def create_post(
        self,
        user_id: str,
        title: str,
        content: str,
        category: Optional[str] = "talk",
        images: Optional[List[UploadFile]] = [],
    ) -> Optional[str]:

        # 1) 유저 존재 체크 (DB → Repository)
        user_exists = await self.community_repository.get_user(user_id)
        if not user_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유저가 없습니다.",
            )

        # 2) post_id 생성 및 중복 체크
        post_id = str(uuid.uuid4())
        duplicate = await self.community_repository.check_duplicate_post(post_id)
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 존재하는 게시글 ID입니다.",
            )

        # 3) DB에 posts INSERT
        created = await self.community_repository.insert_post(
            post_id=post_id,
            user_id=user_id,
            title=title,
            content=content,
            category=category,
        )
        if not created:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="게시글 생성 실패",
            )

        # 4) 이미지 업로드 + DB 저장 (서비스는 이미지 업로드 책임)
        for idx, file in enumerate(images):
            if not file:
                continue

            # 이미지 원본 업로드
            s3_key = f"community/{post_id}/"
            filename = generate_filename(file.filename)
            file.file.seek(0)
            image_bytes = file.file.read()
            origin_file = io.BytesIO(image_bytes)

            if not upload_file_to_s3(origin_file, s3_key, filename):
                raise HTTPException(
                    status_code=500, detail=f"S3 업로드 실패: {file.filename}"
                )

            # 썸네일 생성 (첫 번째 이미지만)
            if idx == 0:
                image = Image.open(io.BytesIO(image_bytes))
                image = ImageOps.exif_transpose(image)
                if image.mode != "RGB":
                    image = image.convert("RGB")

                width, height = image.size
                scale = 200 / min(width, height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                image = image.resize((new_width, new_height), Image.LANCZOS)

                thumb_io = io.BytesIO()
                image.save(thumb_io, format="JPEG", quality=95)
                thumb_io.seek(0)

                thumbnail_key = f"community/{post_id}/thumbnail/"
                thumbnail_name = f"{post_id}_thumbnail.jpg"

                if not upload_file_to_s3(thumb_io, thumbnail_key, thumbnail_name):
                    raise HTTPException(
                        status_code=500, detail=f"섬네일 업로드 실패: {file.filename}"
                    )

            # DB에 이미지 URL 저장
            url = f"{CLOUDFRONT_URL}/{s3_key}{filename}"
            await self.community_repository.insert_post_images(
                post_id, user_id, idx, url
            )

        # 5) image_list 조회하여 history 기록
        image_urls = await self.community_repository.get_post_images(post_id)
        image_list = ", ".join(image_urls) if image_urls else None

        await self.community_repository.create_post_history(
            post_id=post_id,
            user_id=user_id,
            title=title,
            content=content,
            image_list=image_list,
        )

        return post_id

    async def edit_post(
        self,
        post_id: str,
        user_id: str,
        title: str,
        content: str,
        url_list: List[str],
        images: List[UploadFile],
    ):
        # 1) 문자열 한 덩어리로 들어오면 파싱
        if len(url_list) == 1 and "," in url_list[0]:
            url_list = [u.strip() for u in url_list[0].split(",")]
        keep_images = [u.strip() for u in url_list]

        # 2) 새 이미지 업로드 처리
        new_image_urls = []
        first_image_bytes = None

        if images:
            for idx, file in enumerate(images):
                s3_key = f"community/{post_id}/"
                filename = generate_filename(file.filename)

                file.file.seek(0)
                image_bytes = file.file.read()
                origin_file = io.BytesIO(image_bytes)

                if idx == 0:
                    first_image_bytes = image_bytes

                if not upload_file_to_s3(origin_file, s3_key, filename):
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to upload image {file.filename} to S3",
                    )

                new_image_urls.append(f"{CLOUDFRONT_URL}/{s3_key}{filename}")

            # 3) 첫 번째 이미지로 썸네일 생성
            # ❗ 절대 images[0].file.read() 쓰지 않는다
            image = Image.open(io.BytesIO(first_image_bytes))

            image = ImageOps.exif_transpose(image)
            if image.mode != "RGB":
                image = image.convert("RGB")

            width, height = image.size
            scale = 200 / min(width, height)
            image = image.resize(
                (int(width * scale), int(height * scale)), Image.LANCZOS
            )

            thumb_io = io.BytesIO()
            image.save(thumb_io, format="JPEG")
            thumb_io.seek(0)

            if not upload_file_to_s3(
                thumb_io,
                f"community/{post_id}/thumbnail/",
                f"{post_id}_thumbnail.jpg",
            ):
                raise HTTPException(
                    status_code=500,
                    detail="Failed to upload thumbnail image",
                )

        # 4) DB 업데이트
        success = await self.community_repository.edit_post(
            post_id=post_id,
            user_id=user_id,
            title=title,
            content=content,
            keep_images=keep_images,
            new_image_urls=new_image_urls,
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail="게시글 수정에 실패했습니다.",
            )

        return True

    async def delete_post(self, post_id: str, user_id: str) -> bool:
        owner = await self.community_repository.get_post_owner(post_id)

        if not owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="존재하지 않는 게시글입니다.",
            )
        if owner[0] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="게시글 삭제 권한이 없습니다.",
            )

        await self.community_repository.delete_post(post_id)
        await self.community_repository.insert_post_history(post_id)
        return True

    # 카테고리별 list따로 불러오기.
    async def get_posts(
        self,
        page: int,
        category: Optional[str] = None,
    ) -> List[PostListResponse]:
        rows = await self.community_repository.get_posts(page, category)

        posts = []

        for (
            post_id,
            user_id,
            category_val,
            title,
            content,
            is_admin,
            view_count,
            anonymous,
            created_at,
            images,
            like_user_ids,
            comment_count,
        ) in rows:

            image_list = images.split("||") if images else []
            like_list = like_user_ids.split("||") if like_user_ids else []

            posts.append(
                PostListResponse(
                    id=post_id,
                    userId=user_id,
                    category=category_val,
                    title=title,
                    content=content,
                    isAdmin=is_admin,
                    images=image_list,
                    viewCount=view_count,
                    likeUserIds=like_list,
                    commentCount=comment_count,
                    anonymous=anonymous,
                    createdAt=created_at.strftime("%Y-%m-%d %H:%M:%S"),
                )
            )

        return posts

    async def get_post_detail(self, post_id: str) -> Optional[PostDetailResponse]:
        detail = await self.community_repository.get_post_detail(post_id)

        return PostDetailResponse(
            id=detail["post_id"],
            userId=detail["user_id"],
            category=detail["category"],
            title=detail["title"],
            content=detail["content"],
            isAdmin=detail["is_admin"],
            viewCount=detail["view_count"],
            likeCount=len(detail["like_user_ids"]),
            images=detail["images"],
            likeUserIds=detail["like_user_ids"],
            comments=[
                CommentResponse(
                    id=row[0],
                    postId=row[1],
                    userId=row[2],
                    content=row[3],
                    anonymous=row[4],
                    likeCount=row[6],
                    createdAt=row[5].strftime("%Y-%m-%d %H:%M:%S"),
                )
                for row in detail["comments"]
            ],
            anonymous=detail["anonymous"],
            createdAt=detail["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
        )

    # 역시 카테고리, is_admin 필요
    async def search_posts(
        self,
        search: str,
        category: Optional[str] = None,
    ) -> List[PostListResponse]:
        rows = await self.community_repository.search_posts(search, category)

        posts = []

        for (
            post_id,
            user_id,
            category_val,
            title,
            content,
            is_admin,
            view_count,
            anonymous,
            created_at,
            images,
            like_user_ids,
            comment_count,
        ) in rows:

            posts.append(
                PostListResponse(
                    id=post_id,
                    userId=user_id,
                    category=category_val,
                    title=title,
                    content=content,
                    isAdmin=is_admin,
                    images=images.split("||") if images else [],
                    viewCount=view_count,
                    likeUserIds=like_user_ids.split("||") if like_user_ids else [],
                    commentCount=comment_count,
                    anonymous=anonymous,
                    createdAt=created_at.strftime("%Y-%m-%d %H:%M:%S"),
                )
            )

        return posts

    async def like_post(self, user_id: str, post_id: str):
        result = await self.community_repository.like_post(user_id, post_id)

        if not result:
            raise HTTPException(status_code=400, detail="좋아요 처리에 실패했습니다.")

        return True

    async def cancel_post_like(self, user_id: str, post_id: str):
        result = await self.community_repository.cancel_post_like(user_id, post_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail="좋아요를 누르지 않은 게시글입니다.",
            )

        return True

    async def block_post(self, user_id: str, post_id: str):
        result = await self.community_repository.block_post(user_id, post_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail="존재하지 않는 사용자이거나 게시글입니다.",
            )

        return True

    # TODO: 신고당한 게시글의 유저는 어떻게 처리할까. 백에서 처리? 프론트에서 처리?
    async def report_post(self, report_post_id: str, report_user_id: str, reason: str):
        report = await self.community_repository.report_post(
            report_post_id, report_user_id, reason
        )

        if not report:
            raise HTTPException(
                status_code=404,
                detail="존재하지 않는 사용자이거나 게시글입니다.",
            )

        return True

    async def create_comment(self, post_id: str, user_id: str, content: str):
        result = await self.community_repository.create_comment(
            post_id, user_id, content
        )

        if not result:
            raise HTTPException(
                status_code=404,
                detail="존재하지 않거나 삭제된 게시글입니다.",
            )

        return True

    async def get_comments(self, post_id: str):
        rows = await self.community_repository.get_comments(post_id)

        if rows is None:
            raise HTTPException(
                status_code=404,
                detail="존재하지 않거나 삭제된 게시글입니다.",
            )

        comments = [
            CommentResponse(
                id=row[0],
                postId=row[1],
                userId=row[2],
                content=row[3],
                anonymous=row[4],
                likeCount=row[6],
                createdAt=row[5].strftime("%Y-%m-%d %H:%M:%S"),
            )
            for row in rows
        ]

        return comments

    async def like_comment(self, user_id: str, comment_id: str):
        result = await self.community_repository.like_comment(user_id, comment_id)

        if not result:
            raise HTTPException(status_code=400, detail="댓글 좋아요에 실패했습니다.")

        return True

    async def cancel_like_comment(self, user_id: str, comment_id: str):
        result = await self.community_repository.cancel_like_comment(
            user_id, comment_id
        )

        if not result:
            raise HTTPException(
                status_code=400, detail="댓글 좋아요 취소에 실패했습니다."
            )

        return True

    async def edit_comment(self, user_id: str, comment_id: int, content: str):
        result = await self.community_repository.edit_comment(
            user_id=user_id,
            comment_id=comment_id,
            content=content,
        )

        if not result:
            raise HTTPException(status_code=400, detail="댓글 수정에 실패했습니다.")

        return True

    async def delete_comment(self, user_id: str, comment_id: int) -> bool:
        result = await self.community_repository.delete_comment(
            user_id=user_id,
            comment_id=comment_id,
        )

        if not result:
            raise HTTPException(
                status_code=400,
                detail="댓글 삭제에 실패했습니다.",
            )

        return True

    async def get_my_posts(self, user_id: str):
        rows = await self.community_repository.get_my_posts(user_id)

        result = []
        for row in rows:
            (
                post_id,
                user_id,
                category,
                title,
                content,
                is_admin,
                view_count,
                anonymous,
                created_at,
                images,
                like_user_ids,
                comment_count,
            ) = row

            result.append(
                PostListResponse(
                    id=post_id,
                    userId=user_id,
                    category=category,
                    title=title,
                    content=content,
                    isAdmin=is_admin,
                    images=images.split(",") if images else [],
                    viewCount=view_count,
                    likeUserIds=like_user_ids.split(",") if like_user_ids else [],
                    commentCount=comment_count,
                    anonymous=anonymous,
                    createdAt=created_at.strftime("%Y-%m-%d %H:%M:%S"),
                )
            )

        return result

    async def get_my_comments(self, user_id: str):
        rows = await self.community_repository.get_my_comments(user_id)

        comments = []
        for row in rows:
            (
                comment_id,
                post_id,
                user_id,
                content,
                anonymous,
                created_at,
                like_count,
            ) = row

            comments.append(
                CommentResponse(
                    id=comment_id,
                    postId=post_id,
                    userId=user_id,
                    content=content,
                    anonymous=anonymous,
                    likeCount=like_count,
                    createdAt=created_at.strftime("%Y-%m-%d %H:%M:%S"),
                )
            )

        return comments

    async def block_comment(self, user_id: str, comment_id: int):
        success = await self.community_repository.block_comment(user_id, comment_id)
        if not success:
            raise HTTPException(400, "댓글 차단 실패")
        return True

    async def report_comment(
        self, report_comment_id: int, report_user_id: str, reason: str
    ) -> bool:
        try:
            reported = self.community_repository.report_comment(
                report_comment_id=report_comment_id,
                report_user_id=report_user_id,
                reason=reason,
            )
            return reported
        except Exception as e:
            logger.error(f"댓글 신고 실패: {e}")
            return False

    async def fetch_post_user_id(self, post_id: str) -> Optional[str]:
        try:
            user_id = await self.community_repository.fetch_post_user_id(post_id)
            logger.info(f"게시글 작성자 ID 조회 성공: {user_id}")
            return user_id
        except Exception as e:
            logger.error(f"게시글 작성자 ID 조회 실패: {e}")
            return None

    async def fetch_post_like_count(self, post_id: str) -> Optional[str]:
        try:
            count = await self.community_repository.fetch_post_like_count(post_id)
            logger.info(f"좋아요 수 조회 성공: {count}")
            return count
        except Exception as e:
            logger.error(f"좋아요 수 조회 실패: {e}")
            return None
