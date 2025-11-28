from fastapi import HTTPException, status
from app.db.db_connection import db
from typing import List, Optional
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class BizRepository:
    def __init__(self, db):
        self.db = db

    async def get_biz_account(self, biz_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT *
                    FROM biz_account
                    WHERE biz_id = %s
                    """,
                    (biz_id,),
                )
                biz = await cur.fetchone()
                return biz

    async def update_biz_tokens(
        self,
        biz_id: str,
        access_token: str,
        refresh_token: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE biz_account
                    SET access_token = %s, refresh_token = %s
                    WHERE biz_id = %s
                    """,
                    (access_token, refresh_token, biz_id),
                )

    async def get_my_biz_account_info(self, biz_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT  
                        b.biz_id,
                        b.store_type,
                        b.tags,
                        b.address,
                        b.business_hours,
                        b.phone,
                        b.manager_phone,
                        b.latitude,
                        b.longitude,
                        (
                            SELECT JSON_ARRAYAGG(t.url)
                            FROM (
                                SELECT bi.url
                                FROM biz_images bi
                                WHERE bi.biz_id = b.biz_id
                                ORDER BY bi.index
                            ) t
                        ) AS image_urls
                    FROM biz_account b
                    WHERE b.biz_id = %s
                    """,
                    (biz_id,),
                )
                biz_info = await cur.fetchone()
                return biz_info

    async def upload_biz_images(
        self, biz_id: str, image_urls: List[str], start_index: int
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                for idx, image_url in enumerate(image_urls, start=start_index):
                    await cur.execute(
                        """
                        INSERT INTO biz_images (biz_id, `index`, url, use_yn)
                        VALUES (%s, %s, %s, TRUE)
                        """,
                        (biz_id, idx, image_url),
                    )

    async def delete_biz_account(
        self,
        biz_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE biz_account
                    SET leaved = TRUE
                    WHERE biz_id = %s
                    """,
                    (biz_id,),
                )

    async def create_biz_coupon(
        self,
        biz_id: str,
        title: str,
        content: str,
        start_date: str,
        expired_date: str,
        amount: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO biz_coupon
                    (biz_id, title, content, amount, start_date, expired_date) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (biz_id, title, content, amount, start_date, expired_date),
                )

    async def update_biz_coupon(
        self,
        coupon_id: int,
        title: str,
        content: str,
        hashtags: str,
        valid_date: str,
        image_url: Optional[str] = None,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE biz_coupons
                    SET title = %s,
                        content = %s,
                        hashtags = %s,
                        valid_date = %s,
                        image_url = %s
                    WHERE id = %s AND deleted = FALSE
                    """,
                    (
                        title,
                        content,
                        hashtags,
                        valid_date,
                        image_url,
                        coupon_id,
                    ),
                )
