from fastapi import HTTPException, status
from app.db.db_connection import db
from typing import List, Optional
from app.utils.logging_config import get_logger
from app.db.biz import BizDetailRow, BizCouponRow

logger = get_logger(__name__)


class BizRepository:
    def __init__(self, db):
        self.db = db

    async def get_biz_id(self, user_id: str) -> str:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT biz_id
                    FROM biz_account
                    WHERE id = %s
                    """,
                    (user_id,),
                )
                result = await cur.fetchone()
                if result:
                    return result[0]
                else:
                    return None

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

    async def get_my_biz_account_info(self, user_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT  
                        b.id,
                        b.biz_id,
                        b.store_type,
                        b.store_name,
                        b.tags,
                        b.address,
                        b.business_hours,
                        b.phone,
                        b.manager_phone,
                        b.latitude,
                        b.longitude,
                        b.credit,
                        b.marketing_agree,
                        b.night_agree,
                        b.personal_chat_alarm_agree,
                        b.group_chat_alarm_agree,
                        b.post_comment_alarm_agree,
                        b.post_like_alarm_agree,
                        b.profile_alarm_agree,
                        b.secret_alarm_agree,
                        b.feed_like_alarm_agree,
                        b.feed_comment_alarm_agree,

                        -- 비즈 이미지
                        (
                            SELECT JSON_ARRAYAGG(t.url)
                            FROM (
                                SELECT bi.url
                                FROM biz_images bi
                                WHERE bi.biz_id = b.biz_id
                                ORDER BY bi.index
                            ) t
                        ) AS image_urls,

                        -- 차단 목록
                        (
                            SELECT JSON_ARRAYAGG(ub.blocked_user_id)
                            FROM user_block_list ub
                            WHERE ub.block_user_id = u.id
                        ) AS block_user_list,

                        -- 즐겨찾기 목록
                        (
                            SELECT JSON_ARRAYAGG(favorite_user_id)
                            FROM users_favorite_list
                            WHERE user_id = u.id
                        ) AS favorite_user_list,

                        -- pushRead
                        (
                            SELECT EXISTS(
                                SELECT 1
                                FROM push_user_log pul
                                WHERE pul.user_no = u.user_no 
                                AND pul.delivery_state = 'DELIVERED'
                            )
                        ) AS push_read,

                        -- profileRead
                        (
                            SELECT EXISTS(
                                SELECT 1
                                FROM push_user_log pul
                                WHERE pul.user_no = u.user_no 
                                AND pul.status = 'SUCCESS'
                                AND pul.delivery_state = 'DELIVERED' 
                                AND pul.push_type = 'profile'
                            )
                        ) AS profile_read,

                        -- hasSecretFeed
                        (
                            SELECT EXISTS(
                                SELECT 1
                                FROM feeds f
                                WHERE f.user_id = u.id
                                AND f.secret_status = TRUE
                                AND f.deleted = FALSE
                            )
                        ) AS has_secret_feed,
                        
                        -- 팔로워 수
                        (
                            SELECT COUNT(*)
                            FROM users_follow_list fl
                            WHERE fl.following_user_id = b.id
                        ) AS follower_count,
                        
                        -- 팔로잉 수
                        (
                            SELECT COUNT(*)
                            FROM users_follow_list fl
                            WHERE fl.follower_user_id = b.id
                        ) AS following_count,

                        -- 팔로잉 리스트
                        (
                            SELECT JSON_ARRAYAGG(fl.following_user_id)
                            FROM users_follow_list fl
                            WHERE fl.follower_user_id = b.id
                        ) AS following_list
                        
                    FROM biz_account b
                    LEFT JOIN users u ON u.id = b.id
                    WHERE b.id = %s
                    """,
                    (user_id,),
                )

                row = await cur.fetchone()
                if not row:
                    return None

                columns = [col[0] for col in cur.description]
                row_dict = dict(zip(columns, row))
                return BizDetailRow(**row_dict)

    async def get_biz_detail(self, biz_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT  
                        b.id,
                        b.biz_id,
                        b.store_type,
                        b.store_name,
                        b.tags,
                        b.address,
                        b.business_hours,
                        b.phone,
                        b.manager_phone,
                        b.latitude,
                        b.longitude,
                        b.credit,
                        b.marketing_agree,
                        b.night_agree,
                        b.personal_chat_alarm_agree,
                        b.group_chat_alarm_agree,
                        b.post_comment_alarm_agree,
                        b.post_like_alarm_agree,
                        b.profile_alarm_agree,
                        b.secret_alarm_agree,
                        b.feed_like_alarm_agree,
                        b.feed_comment_alarm_agree,

                        -- 비즈 이미지
                        (
                            SELECT JSON_ARRAYAGG(t.url)
                            FROM (
                                SELECT bi.url
                                FROM biz_images bi
                                WHERE bi.biz_id = b.biz_id
                                ORDER BY bi.index
                            ) t
                        ) AS image_urls,

                        -- 차단 목록
                        (
                            SELECT JSON_ARRAYAGG(ub.blocked_user_id)
                            FROM user_block_list ub
                            WHERE ub.block_user_id = u.id
                        ) AS block_user_list,

                        -- 즐겨찾기 목록
                        (
                            SELECT JSON_ARRAYAGG(favorite_user_id)
                            FROM users_favorite_list
                            WHERE user_id = u.id
                        ) AS favorite_user_list,

                        -- pushRead
                        (
                            SELECT EXISTS(
                                SELECT 1
                                FROM push_user_log pul
                                WHERE pul.user_no = u.user_no 
                                AND pul.delivery_state = 'DELIVERED'
                            )
                        ) AS push_read,

                        -- profileRead
                        (
                            SELECT EXISTS(
                                SELECT 1
                                FROM push_user_log pul
                                WHERE pul.user_no = u.user_no 
                                AND pul.status = 'SUCCESS'
                                AND pul.delivery_state = 'DELIVERED' 
                                AND pul.push_type = 'profile'
                            )
                        ) AS profile_read,

                        -- hasSecretFeed
                        (
                            SELECT EXISTS(
                                SELECT 1
                                FROM feeds f
                                WHERE f.user_id = u.id
                                AND f.secret_status = TRUE
                                AND f.deleted = FALSE
                            )
                        ) AS has_secret_feed,
                        
                        -- 팔로워 수
                        (
                            SELECT COUNT(*)
                            FROM users_follow_list fl
                            WHERE fl.following_user_id = b.id
                        )
                        AS follower_count,
                        -- 팔로잉 수
                        (
                            SELECT COUNT(*)
                            FROM users_follow_list fl
                            WHERE fl.follower_user_id = b.id
                        )
                        AS following_count

                    FROM biz_account b
                    LEFT JOIN users u ON u.id = b.id
                    WHERE b.id = %s
                    """,
                    (biz_id,),
                )

                row = await cur.fetchone()
                if not row:
                    return None

                columns = [col[0] for col in cur.description]
                row_dict = dict(zip(columns, row))
                return BizDetailRow(**row_dict)

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
        biz_id: str,
        coupon_id: int,
        title: str,
        content: str,
        amount: int,
        start_date: str,
        expired_date: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 1
                    FROM biz_coupon
                    WHERE biz_id = %s AND id= %s AND deleted = FALSE
                    """,
                    (
                        biz_id,
                        coupon_id,
                    ),
                )
                result = await cur.fetchone()
                if not result:
                    return False

                await cur.execute(
                    """
                    UPDATE biz_coupon
                    SET title = %s,
                        content = %s,
                        amount = %s,
                        start_date = %s,
                        expired_date = %s
                    WHERE id = %s AND deleted = FALSE
                    """,
                    (
                        title,
                        content,
                        amount,
                        start_date,
                        expired_date,
                        coupon_id,
                    ),
                )
            await conn.commit()
            return True

    async def delete_biz_coupon(
        self,
        biz_id: str,
        coupon_id: int,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 1
                    FROM biz_coupon
                    WHERE id = %s AND biz_id = %s AND deleted = FALSE
                    """,
                    (coupon_id, biz_id),
                )
                result = await cur.fetchone()
                if not result:
                    return False

                await cur.execute(
                    """
                    UPDATE biz_coupon
                    SET deleted = TRUE
                    WHERE id = %s AND biz_id = %s
                    """,
                    (coupon_id, biz_id),
                )
                return True

    async def fetch_biz_coupons(
        self,
        biz_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 
                        id,
                        biz_id,
                        title,
                        content,
                        start_date,
                        expired_date,
                        amount
                    FROM biz_coupon
                    WHERE biz_id = %s AND deleted = FALSE
                    ORDER BY id DESC
                    """,
                    (biz_id,),
                )
                rows = await cur.fetchall()
                if not rows:
                    return []

                columns = [col[0] for col in cur.description]
                result = []

                for row in rows:
                    row_dict = dict(zip(columns, row))
                    result.append(BizCouponRow(**row_dict))

                return result

    async def answer_biz_review(
        self,
        biz_id: str,
        review_id: int,
        content: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:

                # 리뷰가 해당 업장의 리뷰인지 체크
                await cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM biz_review
                    WHERE id = %s AND biz_id = %s AND deleted = FALSE
                    """,
                    (review_id, biz_id),
                )
                (count,) = await cur.fetchone()
                if count == 0:
                    return False

                # 이미 답변 달린 리뷰인지 체크
                await cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM biz_review_answer_list
                    WHERE review_id = %s AND biz_id = %s
                    """,
                    (review_id, biz_id),
                )
                (exists,) = await cur.fetchone()
                if exists > 0:
                    return False

                await cur.execute(
                    """
                    INSERT INTO biz_review_answer_list (biz_id, review_id, content)
                    VALUES (%s, %s, %s)
                    """,
                    (biz_id, review_id, content),
                )
                await conn.commit()

                return True
