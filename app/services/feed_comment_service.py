from typing import List
from fastapi import HTTPException, status
from datetime import datetime
from app.utils.s3_upload import upload_file_to_s3, generate_filename
from app.db.feed_comment import FeedCommentResponse

from app.utils.logging_config import get_logger
from app.utils.token import get_user_id_from_token

logger = get_logger(__name__)


class FeedCommentService:
    def __init__(self, feed_comment_repository, user_repository):
        self.feed_comment_repository = feed_comment_repository
        self.user_repository = user_repository

    async def create_feed_comment(self, feed_id: str, content: str, token: str):
        user_id = await get_user_id_from_token(token)
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            logger.error("사용자가 없습니다.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )

        # 댓글 생성
        comment_id = await self.feed_comment_repository.create_feed_comment(
            user_id=user_id,
            feed_id=feed_id,
            content=content,
        )

        return True

    async def update_feed_comment(self, comment_id, content, token):
        user_id = await get_user_id_from_token(token)
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            logger.error("사용자가 없습니다.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )
        comment_user_id = await self.feed_comment_repository.fetch_feed_comment_by_id(
            comment_id
        )

        if comment_user_id != user_id:
            logger.error("댓글 수정 권한이 없습니다.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to edit comment.",
            )
        await self.feed_comment_repository.update_feed_comment(
            comment_id=comment_id,
            content=content,
        )

    async def delete_feed_comment(self, comment_id, token):
        user_id = await get_user_id_from_token(token)
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            logger.error("사용자가 없습니다.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )
        comment_user_id = await self.feed_comment_repository.fetch_feed_comment_by_id(
            comment_id
        )

        if comment_user_id != user_id:
            logger.error("댓글 삭제 권한이 없습니다.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to delete comment.",
            )
        await self.feed_comment_repository.delete_feed_comment(
            comment_id=comment_id,
        )

    async def block_feed_comment(self, comment_id, token):
        user_id = await get_user_id_from_token(token)
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            logger.error("사용자가 없습니다.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )

        await self.feed_comment_repository.block_feed_comment(
            comment_id=comment_id,
            user_id=user_id,
        )

    async def report_feed_comment(self, comment_id, reported_user_id, reason, token):
        user_id = await get_user_id_from_token(token)
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            logger.error("사용자가 없습니다.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )

        await self.feed_comment_repository.report_feed_comment(
            comment_id=comment_id,
            user_id=user_id,
            reported_user_id=reported_user_id,
            reason=reason,
        )

    async def get_feed_comment_list(self, feed_id, token):
        user_id = await get_user_id_from_token(token)
        user = await self.user_repository.fetch_active_user(user_id)
        if not user:
            logger.error("사용자가 없습니다.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )

        comments = await self.feed_comment_repository.get_feed_comment_list(
            feed_id=feed_id,
            user_id=user_id,
        )
        comment_list: List[FeedCommentResponse] = []
        for comment in comments:
            comment_list.append(
                FeedCommentResponse(
                    commentId=comment[0],
                    userId=comment[1],
                    content=comment[2],
                    createdAt=comment[3],
                )
            )
        return comment_list
