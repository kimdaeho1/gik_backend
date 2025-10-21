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
                    RETURNING comment_id
                    """,
                    (user_id, feed_id, content),
                )

    async def update_feed_comment(self, comment_id: int, content: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE feed_comments
                    SET content = %s, updated_at = NOW()
                    WHERE comment_id = %s
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
                    WHERE comment_id = %s
                    """,
                    (
                        True,
                        comment_id,
                    ),
                )

    async def block_feed_comment(
        self, comment_id: int, user_id: str, blocked_user_id: str
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO feed_comment_blocks (comment_id, user_id, blocked_user_id)
                    VALUES (%s, %s, %s)
                    """,
                    (comment_id, user_id, blocked_user_id),
                )

    async def report_feed_comment(self, comment_id: int, user_id: str, reason: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO feed_comment_reports (comment_id, user_id, reason)
                    VALUES (%s, %s, %s)
                    """,
                    (comment_id, user_id, reason),
                )

    async def get_feed_comment_list(self, feed_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT comment_id, user_id, content, created_at
                    FROM feed_comments
                    WHERE feed_id = %s AND deleted = %s
                    ORDER BY created_at DESC
                    """,
                    (feed_id, False),
                )
                comments = await cur.fetchall()
                return comments
