from fastapi import UploadFile, HTTPException
from app.db.image import UserSecretResponse
from app.db.db_connection import db
from typing import List, Optional
from app.utils.logging_config import get_logger
from app.utils.firebase_init import init_firebase_admin
from firebase_admin import auth
from app.utils.logging_config import get_logger
from app.db.db_connection import db
import random
from datetime import datetime, timedelta

# 서버 내 전역 캐시 딕셔너리
FEED_CACHE = {}

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
        price: Optional[int] = 10,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO feeds (user_id, feed_id, feed_content, status, secret_status, price)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (user_id, feed_id, content, status, secret_status, price),
                )
                await conn.commit()

    async def update_feed(
        self,
        feed_id: str,
        status: bool,
        secret_status: bool,
        content: Optional[str] = None,
        price: Optional[int] = 10,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE feeds
                    SET feed_content = %s, status = %s, secret_status = %s, price = %s, updated_at = NOW()
                    WHERE feed_id = %s
                    """,
                    (content, status, secret_status, price, feed_id),
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
    ) -> List[str]:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT url
                    FROM feed_images
                    WHERE feed_id = %s AND use_yn = TRUE
                    ORDER BY `index` 
                    """,
                    (feed_id,),
                )
                images = await cur.fetchall()
                feed_image_urls = [url for (url,) in images]
                return feed_image_urls

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
                    SELECT feed_id, user_id, feed_content, status, secret_status, price, created_at, updated_at
                    FROM feeds
                    WHERE feed_id = %s AND deleted = FALSE
                    """,
                    (feed_id,),
                )
                feed = await cur.fetchone()
                return feed

    # TODO: 차단 플로우 처리
    async def get_feed_like_count(self, feed_id: str, user_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM feed_likes fl
                    JOIN users u ON fl.user_id = u.id
                    WHERE fl.feed_id = %s
                    AND u.leaved = FALSE
                    AND fl.user_id NOT IN (
                        SELECT blocked_user_id
                        FROM user_block_list
                        WHERE block_user_id = %s
                    )
                    AND fl.user_id NOT IN (
                        SELECT block_user_id
                        FROM user_block_list
                        WHERE blocked_user_id = %s
                    )
                    """,
                    (feed_id, user_id, user_id),
                )
                query_count = await cur.fetchone()
                return query_count[0]

    # TODO: 차단 플로우 처리
    async def get_feed_comment_count(self, feed_id: str, user_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM feed_comments fc
                    JOIN users u ON fc.user_id = u.id
                    WHERE fc.feed_id = %s
                    AND fc.deleted = FALSE
                    AND u.leaved = FALSE
                    AND fc.user_id NOT IN (
                        SELECT blocked_user_id
                        FROM user_block_list
                        WHERE block_user_id = %s
                    )
                    AND fc.user_id NOT IN (
                        SELECT block_user_id
                        FROM user_block_list
                        WHERE blocked_user_id = %s
                    )
                    """,
                    (feed_id, user_id, user_id),
                )
                query_count = await cur.fetchone()
                return query_count[0]

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
                    SELECT feed_id, user_id, feed_content, status, secret_status, price, created_at, updated_at
                    FROM feeds
                    WHERE user_id = %s AND deleted = %s AND status = %s AND secret_status = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, False, status, secret_status, 5, offset),
                )
                feeds = await cur.fetchall()

                return feeds

    # TODO: 차단 플로우 처리
    async def get_feed_list(self, user_id: str, page: int):
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
                        f.price,
                        f.created_at, 
                        f.updated_at
                    FROM feeds f
                    JOIN users u ON f.user_id = u.id
                    WHERE f.deleted = %s
                    AND u.leaved = FALSE
                    AND NOT EXISTS (
                        SELECT 1 FROM user_block_list ubl
                        WHERE 
                            (ubl.block_user_id = %s AND ubl.blocked_user_id = f.user_id)
                            OR (ubl.block_user_id = f.user_id AND ubl.blocked_user_id = %s)
                    )
                    AND f.feed_id NOT IN (
                        SELECT blocked_feed_id 
                        FROM feed_blocks 
                        WHERE block_user_id = %s
                    )
                    ORDER BY f.created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (False, user_id, user_id, user_id, 5, offset),
                )
                feeds = await cur.fetchall()
                return feeds

    # TODO: 차단 플로우 처리
    async def get_user_feed_list(
        self, user_id: str, target_user_id: str, page: int, secret_status: bool
    ):
        offset = (page - 1) * 5
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 
                        f.feed_id, f.user_id, f.feed_content, f.status, f.secret_status, f.price, f.created_at, f.updated_at
                    FROM feeds f
                    WHERE f.user_id = %s 
                    AND f.secret_status = %s 
                    AND f.deleted = FALSE
                    AND f.feed_id NOT IN (
                        SELECT blocked_feed_id 
                        FROM feed_blocks 
                        WHERE block_user_id = %s
                    )
                    AND NOT EXISTS (
                        SELECT 1
                        FROM user_block_list ub
                        WHERE 
                            (ub.block_user_id = %s AND ub.blocked_user_id = %s)
                            OR
                            (ub.block_user_id = %s AND ub.blocked_user_id = %s)
                    )
                    ORDER BY f.created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (
                        target_user_id,
                        secret_status,
                        user_id,
                        user_id,
                        target_user_id,
                        target_user_id,
                        user_id,
                        5,
                        offset,
                    ),
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

    # TODO: 차단 플로우 처리
    async def get_feed_like_list(self, feed_id: str, user_id: str) -> List[str]:
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
                    AND fl.user_id NOT IN (
                        SELECT blocked_user_id
                        FROM user_block_list
                        WHERE block_user_id = %s
                    )
                    AND fl.user_id NOT IN (
                        SELECT block_user_id
                        FROM user_block_list
                        WHERE blocked_user_id = %s
                    )
                    """,
                    (feed_id, user_id, user_id),
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

    # TODO: 차단 플로우 처리
    async def get_purchase_feed_list(self, user_id: str, page: int):
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
                        f.price,
                        f.created_at
                    FROM feed_purchase_list p
                    JOIN feeds f ON p.feed_id = f.feed_id
                    JOIN users u ON f.user_id = u.id
                    WHERE p.user_id = %s
                    AND f.deleted = FALSE
                    AND u.leaved = FALSE
                    AND f.user_id NOT IN (
                        SELECT blocked_user_id
                        FROM user_block_list
                        WHERE block_user_id = %s
                    )
                    AND f.user_id NOT IN (
                        SELECT block_user_id
                        FROM user_block_list
                        WHERE blocked_user_id = %s
                    )
                    AND f.feed_id NOT IN (
                        SELECT blocked_feed_id 
                        FROM feed_blocks 
                        WHERE block_user_id = %s
                    )
                    ORDER BY p.created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, user_id, user_id, user_id, 5, offset),
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
                    (user_id, -credit_amount, credit_description),
                )

                await cur.execute(
                    """
                    UPDATE users
                    SET credit = credit - %s
                    WHERE id = %s
                    """,
                    (credit_amount, user_id),
                )

    async def fetch_feed_secret_status(
        self,
        feed_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT secret_status
                    FROM feeds
                    WHERE feed_id = %s AND deleted = FALSE
                    """,
                    (feed_id,),
                )
                result = await cur.fetchone()
                return result[0]

    async def fetch_purchase_secret_feed(
        self,
        user_id: str,
        feed_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM feed_purchase_list
                    WHERE user_id = %s AND feed_id = %s
                    """,
                    (user_id, feed_id),
                )
                count = await cur.fetchone()
                return count[0] > 0

    async def get_feed_user_id(
        self,
        feed_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT user_id
                    FROM feeds
                    WHERE feed_id = %s
                    """,
                    (feed_id,),
                )
                result = await cur.fetchone()
                if result:
                    return result[0]

    async def get_feed_user_nickname(
        self,
        user_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT nickname
                    FROM users
                    WHERE id = %s AND leaved = FALSE
                    """,
                    (user_id,),
                )
                result = await cur.fetchone()
                if result:
                    return result[0]

    async def check_purchase_secret_feed(
        self,
        user_id: str,
        feed_id: str,
    ) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM feed_purchase_list
                    WHERE user_id = %s AND feed_id = %s
                    """,
                    (user_id, feed_id),
                )
                count = await cur.fetchone()
                return count[0] > 0

    # TODO: 차단 플로우 처리
    async def get_random_feed_list(self, user_id: str, page: int):
        now = datetime.utcnow()
        offset = (page - 1) * 5

        # 캐시 확인.
        # 유저의 아이디가 가지고있는 캐시 데이터가 있고, 만료 기간이 지나지 않았다면:
        if user_id in FEED_CACHE and FEED_CACHE[user_id]["expires_at"] > now:
            # 캐시에서 피드 ID 리스트를 가져오기
            feed_ids = FEED_CACHE[user_id]["feeds"]
        else:
            # 캐시가 없거나 만료 기간이 지나버렸다면, 랜덤 피드 ID 리스트를 생성하기
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT f.feed_id
                        FROM feeds f
                        JOIN users u ON f.user_id = u.id
                        WHERE f.deleted = FALSE
                        AND u.leaved = FALSE
                        AND NOT EXISTS (
                            SELECT 1
                            FROM user_block_list ubl
                            WHERE 
                                (ubl.block_user_id = %s AND ubl.blocked_user_id = f.user_id)
                                OR (ubl.block_user_id = f.user_id AND ubl.blocked_user_id = %s)
                        )
                        AND f.feed_id NOT IN (
                            SELECT blocked_feed_id 
                            FROM feed_blocks 
                            WHERE block_user_id = %s
                        )
                        """,
                        (user_id, user_id, user_id),
                    )
                    query = await cur.fetchall()
                    feed_ids = [row[0] for row in query]

            # 랜덤으로 셔플해서 캐시에 저장하기
            random.shuffle(feed_ids)
            # 캐시에 저장할때는 피드의 Id리스트와 만료 시간을 같이 저장
            FEED_CACHE[user_id] = {
                "feeds": feed_ids,
                "expires_at": now + timedelta(minutes=1),
            }

        # 페이지 단위로 피드 ID 추출하기
        paging_ids = feed_ids[offset : offset + 5]

        # 캐시 끝까지 도달 시 새로 생성 (끝으로 가면 피드가 없어짐)
        if not paging_ids:
            return []

        # 실제 피드 데이터 가져오기
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                placeholders = ",".join(["%s"] * len(paging_ids))

                query = (
                    """
                    SELECT 
                        f.feed_id,
                        f.user_id,
                        f.feed_content,
                        f.status,
                        f.secret_status,
                        f.price,
                        f.created_at,
                        f.updated_at
                    FROM feeds f
                    JOIN users u ON f.user_id = u.id
                    WHERE f.feed_id IN ({})
                    """
                ).format(placeholders)

                await cur.execute(query, tuple(paging_ids))
                feeds = await cur.fetchall()
                return feeds

    # 피드의 가격 가져오기
    async def get_feed_price(self, feed_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT price
                    FROM feeds
                    WHERE feed_id = %s AND deleted = FALSE
                    """,
                    (feed_id,),
                )
                result = await cur.fetchone()
                if result:
                    return result[0]

    # (구매했다면) 리베이트 해주기
    async def purchased_feed_rebate(
        self, feed_user_id: str, rebate_amount: int, description: str
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO credit_history (user_id, amount, description)
                    VALUES (%s, %s, %s)
                    """,
                    (feed_user_id, rebate_amount, description),
                )

                await cur.execute(
                    """
                    UPDATE users
                    SET credit = credit + %s
                    WHERE id = %s
                    """,
                    (rebate_amount, feed_user_id),
                )

    async def get_feed_status(
        self,
        feed_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT secret_status
                    FROM feeds
                    WHERE feed_id = %s AND deleted = FALSE
                    """,
                    (feed_id,),
                )
                result = await cur.fetchone()
                if result:
                    return result[0]

    async def get_feed_image(
        self,
        feed_id: str,
    ) -> Optional[str]:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT url
                    FROM feed_images
                    WHERE feed_id = %s AND use_yn = TRUE
                    ORDER BY `index` ASC
                    LIMIT 1
                    """,
                    (feed_id,),
                )
                result = await cur.fetchone()
                if result:
                    return result[0]
                return None

    async def get_user_profile_image(
        self,
        user_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT url
                    FROM user_images
                    WHERE user_id = %s AND use_yn = TRUE
                    LIMIT 1
                    """,
                    (user_id,),
                )
                result = await cur.fetchone()
                if result:
                    return result[0]

    # TODO: 차단 플로우 처리
    async def fetch_feed_purchase_list_with_blind_profile(
        self,
        feed_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT
                        u.id AS userId,
                        u.nickname AS nickname,
                        u.age AS age,
                        u.height AS height,
                        u.weight AS weight,
                        CASE
                            WHEN fb.feed_id IS NOT NULL THEN TRUE
                            ELSE FALSE
                        END AS isPurchase
                    FROM feed_purchase_list fp
                    JOIN users u 
                        ON fp.user_id = u.id
                    JOIN feeds f 
                        ON f.feed_id = fp.feed_id
                    LEFT JOIN feed_blind_profile_purchase_list fb
                        ON fb.feed_id = fp.feed_id
                        AND fb.user_id = fp.user_id
                    WHERE fp.feed_id = %s
                    AND u.leaved = FALSE
                    AND f.deleted = FALSE
                    AND NOT EXISTS (
                        SELECT 1
                        FROM user_block_list ub
                        WHERE ub.block_user_id = f.user_id
                            AND ub.blocked_user_id = fp.user_id
                    )
                    AND NOT EXISTS (
                        SELECT 1
                        FROM user_block_list ub
                        WHERE ub.block_user_id = fp.user_id
                            AND ub.blocked_user_id = f.user_id
                    )
                    ORDER BY fp.created_at DESC
                    """,
                    (feed_id,),
                )
                purchase_list = await cur.fetchall()
                return purchase_list

    async def feed_blind_profile_purchase(
        self,
        feed_id: str,
        user_id: str,
        target_user_id: str,
        credit_amount: int,
        credit_description: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO feed_blind_profile_purchase_list (feed_id, user_id)
                    VALUES (%s, %s)
                    """,
                    (feed_id, target_user_id),
                )

                await cur.execute(
                    """
                    INSERT INTO credit_history (user_id, amount, description)
                    VALUES (%s, %s, %s)
                    """,
                    (user_id, -credit_amount, credit_description),
                )

                await cur.execute(
                    """
                    UPDATE users
                    SET credit = credit - %s
                    WHERE id = %s
                    """,
                    (credit_amount, user_id),
                )

                await conn.commit()
                return True

    async def favorite_user_feed_list(
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
                        f.price,
                        f.created_at, 
                        f.updated_at
                    FROM feeds f
                    JOIN users_favorite_list ufl ON f.user_id = ufl.favorite_user_id
                    JOIN users u ON f.user_id = u.id
                    WHERE ufl.user_id = %s
                    AND f.deleted = FALSE
                    AND u.leaved = FALSE
                    AND NOT EXISTS (
                        SELECT 1 FROM user_block_list ubl
                        WHERE 
                            (ubl.block_user_id = %s AND ubl.blocked_user_id = f.user_id)
                            OR (ubl.block_user_id = f.user_id AND ubl.blocked_user_id = %s)
                    )
                    AND f.feed_id NOT IN (
                        SELECT blocked_feed_id 
                        FROM feed_blocks 
                        WHERE block_user_id = %s
                    )
                    ORDER BY f.created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, user_id, user_id, user_id, 5, offset),
                )
                feeds = await cur.fetchall()
                return feeds
