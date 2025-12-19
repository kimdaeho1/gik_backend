from fastapi import HTTPException, status
from app.db.db_connection import db
from typing import List, Optional
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class GiftRepository:
    def __init__(self, db):
        self.db = db

    async def get_gifticon_goods(self, page: int):
        offset = (page - 1) * 20
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT *
                    FROM gifticon_product
                    LIMIT %s OFFSET %s
                    """,
                    (20, offset),
                )
                rows = await cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                goods_list = [dict(zip(columns, row)) for row in rows]

                return goods_list

    async def get_gifticon_list_by_brand_name(self, brand_name: str) -> List[dict]:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT *
                    FROM gifticon_product
                    WHERE brand_name = %s
                    """,
                    (brand_name,),
                )
                rows = await cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                goods_list = [dict(zip(columns, row)) for row in rows]

                return goods_list
