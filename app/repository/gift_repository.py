from fastapi import HTTPException, status
from app.db.db_connection import db
from typing import List, Optional
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class GiftRepository:
    def __init__(self, db):
        self.db = db

    async def get_gifticon_goods(
        self,
        page: int,
        brand_name: Optional[str] = None,
    ):
        offset = (page - 1) * 20
        where_sql = ""
        params = []

        if brand_name:
            where_sql = "WHERE brand_name = %s"
            params.append(brand_name)

        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"""
                    SELECT *
                    FROM gifticon_product
                    {where_sql}
                    LIMIT %s OFFSET %s
                    """,
                    (*params, 20, offset),
                )
                rows = await cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in rows]

    async def get_goods_category_list(self) -> List[dict]:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT DISTINCT category_detail
                    FROM gifticon_product
                    """
                )
                rows = await cur.fetchall()
                categories = [row[0] for row in rows]

                return categories

    async def get_goods_category_list(self) -> List[dict]:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT
                        category_detail,
                        MIN(category_image) AS category_image
                    FROM gifticon_product
                    GROUP BY category_detail
                    ORDER BY FIELD(
                        category_detail,
                        '커피/음료',
                        '베이커리/도넛',
                        '치킨',
                        '피자',
                        '버거',
                        '아이스크림',
                        '영화',
                        '외식',
                        '편의점',
                        '마트',
                        '마트상품권',
                        '백화점상품권',
                        '생활/가전/디지털',
                        '건강/식품/주방',
                        '도서',
                        '음악',
                        '주유상품권',
                        '용역서비스',
                        '기타상품권',
                        '3사 통합데이터 상품',
                        '올레'
                    )
                    """
                )
                rows = await cur.fetchall()

                return [
                    {
                        "categoryName": row[0],
                        "categoryImage": row[1],
                    }
                    for row in rows
                ]
