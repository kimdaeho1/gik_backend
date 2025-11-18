from fastapi import UploadFile, HTTPException, status
from typing import List, Optional
from app.utils.logging_config import get_logger


logger = get_logger(__name__)


class CommunityRepository:
    def __init__(self, db):
        self.db = db

    async def create_post(
        self,
        user_id: str,
        title: str,
        content: str,
        catetory: Optional[str],
        images: Optional[List[UploadFile]],
    ): ...

    async def edit_post(
        self,
        post_id: str,
        user_id: str,
        title: str,
        content: str,
        url_list: List[str],
        images: List[UploadFile],
    ): ...

    async def delete_post(self, post_id: str, user_id: str): ...

    async def get_posts(
        self,
        page: int,
        category: Optional[str] = None,
    ): ...

    async def get_post_detail(self, post_id: str): ...

    async def search_posts(
        self,
        search: str,
        category: Optional[str] = None,
    ): ...

    async def like_post(
        self,
        user_id: str,
        post_id: str,
    ): ...

    async def cancel_post_like(self, user_id: str, post_id: str): ...

    async def block_post(self, user_id: str, post_id: str): ...

    async def report_post(
        self, report_post_id: str, report_user_id: str, reason: str
    ): ...

    async def create_comment(
        self,
        post_id: str,
        user_id: str,
        content: str,
    ): ...

    async def get_comments(
        self,
        post_id: str,
    ): ...

    async def like_comment(
        self,
        user_id: str,
        comment_id: str,
    ): ...

    async def cancel_like_comment(
        self,
        user_id: str,
        comment_id: str,
    ): ...

    async def edit_comment(
        self,
        user_id: str,
        comment_id: str,
        content: str,
    ): ...

    async def delete_comment(self, user_id: str, comment_id: int) -> bool: ...

    async def get_my_posts(self, user_id: str): ...

    async def get_my_comments(self, user_id: str): ...

    async def block_comment(self, user_id: str, comment_id: int): ...

    async def report_comment(
        self, report_comment_id: int, report_user_id: str, reason: str
    ): ...

    async def fetch_post_user_id(self, post_id: str) -> Optional[str]:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT user_id
                    FROM posts
                    WHERE post_id = %s AND deleted = %s
                    """,
                    (post_id, False),
                )
                result = await cur.fetchone()
                if result:
                    return result[0]

    async def fetch_post_like_count(self, post_id: str) -> Optional[str]:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM post_likes 
                    WHERE post_id = %s
                    """,
                    (post_id,),
                )
                result = await cur.fetchone()
                if result:
                    return result[0]
