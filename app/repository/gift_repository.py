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

    async def get_category_brand_list(self, category: str) -> List[dict]:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT DISTINCT brand_name, brand_icon
                    FROM gifticon_product
                    WHERE category_detail = %s
                    """,
                    (category,),
                )
                rows = await cur.fetchall()
                brand_list = [
                    {"brandName": row[0], "brandIcon": row[1]} for row in rows
                ]
                return brand_list

    async def get_user_phone_number(self, user_id: str) -> str:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT phone
                    FROM users
                    WHERE id = %s
                    """,
                    (user_id,),
                )
                row = await cur.fetchone()
                if not row:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="사용자를 찾을 수 없습니다.",
                    )
                return row[0]

    async def create_purchase(
        self,
        user_id: str,
        goods_code: str,
        tr_id: str,
    ) -> dict:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()
                    await cur.execute(
                        """
                        SELECT price_real
                        FROM gifticon_product
                        WHERE goods_code = %s
                          AND is_active = 1
                          AND goods_state = 'SALE'
                        """,
                        (goods_code,),
                    )
                    row = await cur.fetchone()
                    if not row:
                        raise HTTPException(404, "판매 중인 상품이 아닙니다.")

                    price_real = row[0]
                    price_credit = price_real // 50

                    await cur.execute(
                        """
                        SELECT dolphin_credit
                        FROM users
                        WHERE id = %s
                        FOR UPDATE
                        """,
                        (user_id,),
                    )
                    user_row = await cur.fetchone()
                    if user_row[0] < price_credit:
                        raise HTTPException(400, "크레딧 부족")

                    await cur.execute(
                        """
                        UPDATE users
                        SET dolphin_credit = dolphin_credit - %s
                        WHERE id = %s
                        """,
                        (price_credit, user_id),
                    )

                    await cur.execute(
                        """
                        INSERT INTO gifticon_purchase
                        (user_id, goods_code, tr_id, price_real, price_credit, status)
                        VALUES (%s, %s, %s, %s, %s, 'PENDING')
                        """,
                        (user_id, goods_code, tr_id, price_real, price_credit),
                    )

                    await conn.commit()

                    return {
                        "price_real": price_real,
                        "price_credit": price_credit,
                    }

                except Exception:
                    await conn.rollback()
                    raise

    async def mark_sent(self, tr_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE gifticon_purchase
                    SET status = 'SENT'
                    WHERE tr_id = %s
                    """,
                    (tr_id,),
                )
                await conn.commit()

    async def cancel_purchase(
        self,
        tr_id: str,
        user_id: str,
        refund_credit: int,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await conn.begin()

                # 크레딧 복구
                await cur.execute(
                    """
                    UPDATE users
                    SET dolphin_credit = dolphin_credit + %s
                    WHERE id = %s
                    """,
                    (refund_credit, user_id),
                )

                # 상태 변경
                await cur.execute(
                    """
                    UPDATE gifticon_purchase
                    SET status = 'CANCELED'
                    WHERE tr_id = %s
                    """,
                    (tr_id,),
                )

                await conn.commit()
