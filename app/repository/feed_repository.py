from fastapi import UploadFile, HTTPException
from app.db.image import UserSecretResponse
from app.db.db_connection import db
from typing import List, Optional
from app.utils.logging_config import get_logger
from app.utils.firebase_init import init_firebase_admin
from firebase_admin import auth
from app.utils.logging_config import get_logger
from app.db.db_connection import db

logger = get_logger(__name__)


class FeedRepository:
    def __init__(self, db):
        self.db = db

    # 내 피드인지 확인하는 함수. 내 피드가 아니라면 return False.
    async def is_owner(
        self,
        user_id: str,
        feed_id: str,
    ) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT COUNT(*) 
                    FROM feeds
                    WHERE feed_id = %s AND user_id = %s
                    """,
                    (feed_id, user_id),
                )
                count = await cur.fetchone()
                # feed_id와 일치하는 user_id가 없다면, 내 피드가 아님.
                if count == 0:
                    return False
                return True

    async def create_feed(
        self,
        feed_id: str,
        user_id: str,
        status: bool,
        secret_status: bool,
        content: Optional[str] = None,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO feeds (user_id, feed_id, feed_content, status, secret_status)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (user_id, feed_id, content, status, secret_status),
                )
                await conn.commit()

    async def update_feed(
        self,
        feed_id: str,
        status: bool,
        secret_status: bool,
        content: Optional[str] = None,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE feeds
                    SET feed_content = %s, status = %s, secret_status = %s, updated_at = NOW()
                    WHERE feed_id = %s
                    """,
                    (content, status, secret_status, feed_id),
                )

    async def insert_feed_images(
        self,
        feed_id: str,
        user_id: str,
        image_urls: List[str],
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                for index, image_url in enumerate(image_urls):
                    await cur.execute(
                        """
                        INSERT INTO feed_images (feed_id, user_id, `index`, url)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (feed_id, user_id, index, image_url),
                    )

    async def get_feed_images(
        self,
        feed_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT url
                    FROM feed_images
                    WHERE feed_id = %s AND use_yn = True
                    ORDER BY `index` 
                    """,
                    (feed_id,),
                )
                images = await cur.fetchall()
                return [image[0] for image in images]

    async def update_feed_images(
        self,
        feed_id: str,
        user_id: str,
        keep_images: list[str],
        remove_images: list[str],
        uploaded_urls: list[str],
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await conn.begin()

                # 삭제할 이미지 처리
                if remove_images:
                    for url in remove_images:
                        await cur.execute(
                            """
                            UPDATE feed_images
                            SET use_yn = FALSE, updated_at = NOW()
                            WHERE feed_id = %s AND url = %s
                            """,
                            (feed_id, url),
                        )

                # 유지할 이미지 index 재정렬
                for idx, url in enumerate(keep_images):
                    await cur.execute(
                        """
                        UPDATE feed_images
                        SET `index` = %s, updated_at = NOW()
                        WHERE feed_id = %s AND url = %s AND use_yn = TRUE
                        """,
                        (idx, feed_id, url),
                    )

                # 새 이미지 삽입
                start_index = len(keep_images)
                for idx, url in enumerate(uploaded_urls, start=start_index):
                    await cur.execute(
                        """
                        INSERT INTO feed_images (feed_id, user_id, `index`, url)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (feed_id, user_id, idx, url),
                    )

                # 피드 updated_at 갱신
                await cur.execute(
                    """
                    UPDATE feeds
                    SET updated_at = NOW()
                    WHERE feed_id = %s
                    """,
                    (feed_id,),
                )
                await conn.commit()

    async def get_feed(
        self,
        feed_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT feed_id, user_id, feed_content, status, secret_status, created_at, updated_at
                    FROM feeds
                    WHERE feed_id = %s AND deleted = FALSE
                    """,
                    (feed_id,),
                )
                feed = await cur.fetchone()
                return feed

    async def get_feed_like_count(
        self,
        feed_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM feed_likes
                    WHERE feed_id = %s
                    """,
                    (feed_id,),
                )
                query_count = await cur.fetchone()
                count = query_count[0]
                return count

    async def delete_feed(
        self,
        feed_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE feeds
                    SET deleted = %s, updated_at = NOW()
                    WHERE feed_id = %s
                    """,
                    (
                        True,
                        feed_id,
                    ),
                )

    async def report_feed(
        self,
        user_id: str,
        feed_id: str,
        reported_user_id: str,
        reason: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO feed_reports (reported_feed_id, user_id, reported_user_id, reason)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (feed_id, user_id, reported_user_id, reason),
                )

    async def block_feed(
        self,
        user_id: str,
        feed_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO feed_blocks (blocked_feed_id, block_user_id)
                    VALUES (%s, %s)
                    """,
                    (feed_id, user_id),
                )

    async def like_feed(
        self,
        user_id: str,
        feed_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO feed_likes (feed_id, user_id)
                    VALUES (%s, %s)
                    """,
                    (feed_id, user_id),
                )

    async def exist_like_feed(
        self,
        user_id: str,
        feed_id: str,
    ) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM feed_likes
                    WHERE feed_id = %s AND user_id = %s
                    """,
                    (feed_id, user_id),
                )
                count = await cur.fetchone()
                if count[0] == 0:
                    return False
                return True

    async def unlike_feed(
        self,
        user_id: str,
        feed_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    DELETE FROM feed_likes
                    WHERE feed_id = %s AND user_id = %s
                    """,
                    (feed_id, user_id),
                )

    async def get_my_feed_list(
        self,
        user_id: str,
        page: int,
        status: bool,
        secret_status: bool,
    ):
        offset = (page - 1) * 5
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT feed_id, user_id, feed_content, status, secret_status, created_at, updated_at
                    FROM feeds
                    WHERE user_id = %s AND deleted = %s AND status = %s AND secret_status = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, False, status, secret_status, 5, offset),
                )
                feeds = await cur.fetchall()

                return feeds

    async def get_feed_list(self, user_id: str, page: int):
        offset = (page - 1) * 5
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT feed_id, user_id, feed_content, status, secret_status, created_at, updated_at
                    FROM feeds
                    WHERE deleted = %s
                    AND user_id NOT IN (
                        SELECT blocked_user_id 
                        FROM user_block_list 
                        WHERE block_user_id = %s
                    )
                    AND feed_id NOT IN (
                        SELECT blocked_feed_id 
                        FROM feed_blocks 
                        WHERE block_user_id = %s
                    )
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (False, user_id, user_id, 5, offset),
                )
                feeds = await cur.fetchall()
                return feeds

    async def get_user_feed_list(
        self, user_id: str, target_user_id: str, page: int, secret_status: bool
    ):
        offset = (page - 1) * 5
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT feed_id, user_id, feed_content, status, secret_status, created_at, updated_at
                    FROM feeds
                    WHERE user_id = %s AND secret_status = %s AND deleted = FALSE
                    AND feed_id NOT IN(
                        SELECT blocked_feed_id 
                        FROM feed_blocks 
                        WHERE block_user_id = %s
                    )
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (target_user_id, secret_status, user_id, 5, offset),
                )
                feeds = await cur.fetchall()
                return feeds

    async def is_liked_feed(self, feed_id: str, user_id: str) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM feed_likes
                    WHERE feed_id = %s AND user_id = %s
                    """,
                    (feed_id, user_id),
                )
                count = await cur.fetchone()
                if count[0] == 0:
                    return False
                return True

    async def get_feed_like_list(self, feed_id: str) -> List[str]:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT fl.user_id
                    FROM feed_likes AS fl
                    INNER JOIN users AS u
                        ON fl.user_id = u.id
                    WHERE fl.feed_id = %s
                    AND u.leaved = FALSE
                    """,
                    (feed_id,),
                )
                users_list = await cur.fetchall()
                return [user_list[0] for user_list in users_list]

    async def fetch_secret_feed_status(
        self,
        user_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT feed_id
                    FROM feeds
                    WHERE user_id = %s AND secret_status = TRUE AND deleted = FALSE
                    """,
                    (user_id,),
                )
                secret_feeds = await cur.fetchall()
                return len(secret_feeds) > 0

    async def get_purchase_feed_list(
        self,
        user_id: str,
        page: int,
    ):
        offset = (page - 1) * 5
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 
                        f.feed_id, 
                        f.user_id, 
                        f.feed_content, 
                        f.status, 
                        f.secret_status, 
                        f.created_at
                    FROM feed_purchase_list p
                    JOIN feeds f ON p.feed_id = f.feed_id
                    WHERE p.user_id = %s
                      AND f.deleted = FALSE
                      AND f.feed_id NOT IN (
                          SELECT blocked_feed_id 
                          FROM feed_blocks 
                          WHERE block_user_id = %s
                      )
                    ORDER BY f.created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, user_id, 5, offset),
                )
                feeds = await cur.fetchall()
                return feeds

    async def purchase_secret_feed(
        self,
        user_id: str,
        feed_id: str,
        credit_amount: int,
        credit_description: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO feed_purchase_list (user_id, feed_id)
                    VALUES (%s, %s)
                    """,
                    (user_id, feed_id),
                )

                await cur.execute(
                    """
                    INSERT INTO credit_history (user_id, amount, description)
                    VALUES (%s, %s, %s)
                    """,
                    (user_id, credit_amount, credit_description),
                )

                await cur.execute(
                    """
                    UPDATE users
                    SET credit = credit - %s
                    WHERE id = %s
                    """,
                    (credit_amount, user_id),
                )
