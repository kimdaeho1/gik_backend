from fastapi import UploadFile, HTTPException
from app.db.image import UserSecretResponse
from app.db.db_connection import db
from typing import List, Optional
from app.utils.logging_config import get_logger
from app.utils.firebase_init import init_firebase_admin
from firebase_admin import auth
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class FeedCommentRepository:
    def __init__(self, db):
        self.db = db

    async def create_feed_comment(self, user_id: str, feed_id: str, content: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO feed_comments (user_id, feed_id, content)
                    VALUES (%s, %s, %s)
                    """,
                    (user_id, feed_id, content),
                )

    async def update_feed_comment(self, content: str, comment_id: int):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE feed_comments
                    SET content = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (content, comment_id),
                )

    async def delete_feed_comment(self, comment_id: int):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE feed_comments
                    SET deleted = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        True,
                        comment_id,
                    ),
                )

    async def block_feed_comment(self, comment_id: int, user_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO feed_comment_blocks (blocked_comment_id, block_user_id)
                    VALUES (%s, %s)
                    """,
                    (
                        comment_id,
                        user_id,
                    ),
                )

    async def report_feed_comment(
        self, comment_id: int, user_id: str, reported_user_id, reason: str
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO feed_comment_reports (report_user_id, reported_user_id, reported_comment_id, reason)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (user_id, reported_user_id, comment_id, reason),
                )

    # TODO: 차단 플로우 처리
    async def get_feed_comment_list(self, feed_id: str, user_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id, user_id, content, created_at
                    FROM feed_comments
                    WHERE feed_id = %s
                    AND deleted = %s
                    AND id NOT IN (
                        SELECT blocked_comment_id
                        FROM feed_comment_blocks
                        WHERE block_user_id = %s
                    )
                    AND user_id NOT IN (
                        SELECT blocked_user_id
                        FROM user_block_list
                        WHERE block_user_id = %s
                    )
                    ORDER BY created_at DESC
                    """,
                    (feed_id, False, user_id, user_id),
                )
                comments = await cur.fetchall()
                return comments

    async def fetch_feed_comment_by_id(self, comment_id: int):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT user_id
                    FROM feed_comments
                    WHERE id = %s
                    """,
                    (comment_id,),
                )
                result = await cur.fetchone()
                if result:
                    return result[0]
                return None
