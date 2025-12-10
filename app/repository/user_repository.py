from fastapi import UploadFile, HTTPException
from app.db.image import UserSecretResponse
from app.db.db_connection import db
from typing import List, Optional
from app.utils.logging_config import get_logger
from app.utils.firebase_init import init_firebase_admin
from app.utils.utils import to_datetime
from firebase_admin import auth
from app.utils.logging_config import get_logger
from app.db.user import (
    UserProfileRow,
    UserDetailRow,
    UserDetailViewRow,
    UserListRow,
    ViewCountRow,
    CountRow,
    ProfileViewRow,
    BizReviewRow,
)
from datetime import datetime
import math

logger = get_logger(__name__)


class UserRepository:
    def __init__(self, db):
        self.db = db

    async def fetch_active_user(self, user_id: str) -> bool:
        """
        유저가 존재하는지 확인
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 1 FROM (
                        SELECT id FROM users WHERE leaved = FALSE
                        UNION
                        SELECT id FROM biz_account WHERE leaved = FALSE
                    ) AS all_accounts
                    WHERE id = %s
                    """,
                    (user_id,),
                )

                user_exist = await cur.fetchone()
                if user_exist:
                    return True
                else:
                    return False

    async def insert_user(self, user_data: tuple) -> None:
        """
        유저 회원가입
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                insert_sql = """
                    INSERT INTO users (
                        id, fcm, sns, name, phone, provider, email, nickname,
                        birthday, age, height, weight, country, position, relation,
                        hashtags, self_introduction, bdsm_type,
                        marketing_agree, service_agree, personal_agree,
                        personal_chat_alarm_agree, group_chat_alarm_agree,
                        post_comment_alarm_agree, post_like_alarm_agree,
                        night_agree, leaved, test_yn
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s, %s
                    )
                """
                # 리턴값이 필요하지 않음
                await cur.execute(insert_sql, user_data)

    async def insert_user_images(
        self, user_id: str, image_urls: List[str], start_index: int
    ):
        """
        유저 이미지 url 삽입
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                for idx, image_url in enumerate(image_urls, start=start_index):
                    await cur.execute(
                        """
                        INSERT INTO user_images (user_id, `index`, url, use_yn)
                        VALUES (%s, %s, %s, TRUE)
                        """,
                        (user_id, idx, image_url),
                    )

    async def insert_secret_images(self, user_id: str, secret_urls: List[str]):
        """
        유저 시크릿 이미지 url삽입
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                for idx, image_url in enumerate(secret_urls):
                    await cur.execute(
                        """
                        INSERT INTO user_secret_images (user_id, `index`, url, use_yn)
                        VALUES (%s, %s, %s, TRUE)
                        """,
                        (user_id, idx, image_url),
                    )
                await cur.execute(
                    "UPDATE users SET secret_yn = TRUE WHERE id = %s",
                    (user_id,),
                )

    async def fetch_my_profile(self, user_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 
                        u.id,
                        u.fcm,
                        u.nickname,
                        u.birthday,
                        u.age,
                        u.height,
                        u.weight,
                        u.sns,
                        u.relation,
                        u.position,
                        u.country,
                        u.hashtags,
                        u.self_introduction,
                        u.bdsm_type,
                        u.talk_style,
                        u.secret_yn,
                        u.credit,
                        u.provider,
                        u.marketing_agree,
                        u.night_agree,
                        u.personal_chat_alarm_agree,
                        u.group_chat_alarm_agree,
                        u.post_comment_alarm_agree,
                        u.post_like_alarm_agree,
                        u.profile_alarm_agree,
                        u.secret_alarm_agree,
                        u.feed_like_alarm_agree,
                        u.feed_comment_alarm_agree,
                        u.banned,
                        u.unbanned_dt,
                        u.last_connected_at,
                        u.latitude,
                        u.longitude,

                        -- 프로필 이미지 리스트
                        (
                            SELECT JSON_ARRAYAGG(t.url)
                            FROM (
                                SELECT ui.url
                                FROM user_images ui
                                WHERE ui.user_id = u.id AND ui.use_yn = TRUE
                                ORDER BY ui.index
                            ) t
                        ) AS profileImages,

                        -- 시크릿 이미지 리스트
                        (
                            SELECT JSON_ARRAYAGG(t.url)
                            FROM (
                                SELECT us.url
                                FROM user_secret_images us
                                WHERE us.user_id = u.id AND us.use_yn = TRUE
                                ORDER BY us.index
                            ) t
                        ) AS secretImages,

                        -- 차단 리스트
                        (
                            SELECT JSON_ARRAYAGG(ub.blocked_user_id)
                            FROM user_block_list ub
                            WHERE ub.block_user_id = u.id
                        ) AS blockUserList,

                        -- 즐겨찾기 리스트
                        (
                            SELECT JSON_ARRAYAGG(favorite_user_id)
                            FROM users_favorite_list
                            WHERE user_id = u.id
                        ) AS favoriteUserList,

                        -- push_read
                        (
                            SELECT EXISTS(
                                SELECT 1
                                FROM push_user_log pul
                                WHERE pul.user_no = u.user_no 
                                AND pul.delivery_state = 'DELIVERED'
                            )
                        ) AS pushRead,

                        -- profile_read
                        (
                            SELECT EXISTS(
                                SELECT 1
                                FROM push_user_log pul
                                WHERE pul.user_no = u.user_no 
                                AND pul.status = 'SUCCESS'
                                AND pul.delivery_state = 'DELIVERED' 
                                AND pul.push_type = 'profile'
                            )
                        ) AS profileRead,

                        -- 광고 시청 횟수
                        (
                            SELECT COUNT(*)
                            FROM credit_history ch
                            WHERE ch.user_id = u.id
                            AND ch.description = '광고 시청 보상'
                            AND ch.created_at >= CONVERT_TZ(CURDATE(), '+09:00', '+00:00')
                            AND ch.created_at < CONVERT_TZ(CURDATE() + INTERVAL 1 DAY, '+09:00', '+00:00')
                        ) AS todayAdCount,

                        -- 시크릿 피드 존재 여부
                        (
                            SELECT EXISTS(
                                SELECT 1
                                FROM feeds f
                                WHERE f.user_id = u.id
                                AND f.secret_status = TRUE
                                AND f.deleted = FALSE
                            )
                        ) AS hasSecretFeed,
                        -- 팔로워 수
                        (
                            SELECT COUNT(*)
                            FROM users_follow_list fl
                            WHERE fl.following_user_id = u.id
                        ) AS followerCount,
                        
                        -- 팔로잉 수
                        (
                            SELECT COUNT(*)
                            FROM users_follow_list fl
                            WHERE fl.follower_user_id = u.id
                        ) AS followingCount,
                        
                        -- 팔로잉 리스트
                        (
                            SELECT JSON_ARRAYAGG(uf.following_user_id)
                            FROM users_follow_list uf
                            WHERE uf.follower_user_id = u.id
                        )
                        AS followingList

                    FROM users u
                    WHERE u.id = %s
                    AND u.leaved = FALSE
                    LIMIT 1;
                    """,
                    (user_id,),
                )

                row = await cur.fetchone()
                if not row:
                    return None

                columns = [col[0] for col in cur.description]
                row_dict = dict(zip(columns, row))
                return UserDetailRow(**row_dict)

    async def fetch_user_profile(self, user_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT
                        u.id,
                        u.fcm,
                        u.nickname,
                        u.birthday,
                        u.age,
                        u.height,
                        u.weight,
                        u.sns,
                        u.relation,
                        u.position,
                        u.country,
                        u.hashtags,
                        u.self_introduction,
                        u.bdsm_type,
                        u.talk_style,
                        u.secret_yn,
                        u.credit,
                        u.provider,
                        u.marketing_agree,
                        u.night_agree,
                        u.personal_chat_alarm_agree,
                        u.group_chat_alarm_agree,
                        u.post_comment_alarm_agree,
                        u.post_like_alarm_agree,
                        u.profile_alarm_agree,
                        u.secret_alarm_agree,
                        u.feed_like_alarm_agree,
                        u.feed_comment_alarm_agree,
                        u.banned,
                        u.unbanned_dt,
                        u.last_connected_at,
                        u.latitude,
                        u.longitude,
                        u.leaved,

                        -- 프로필 이미지 리스트
                        (
                            SELECT JSON_ARRAYAGG(t.url)
                            FROM (
                                SELECT ui.url
                                FROM user_images ui
                                WHERE ui.user_id = u.id AND ui.use_yn = TRUE
                                ORDER BY ui.index
                            ) t
                        ) AS profileImages,

                        -- 시크릿 이미지 리스트
                        (
                            SELECT JSON_ARRAYAGG(t.url)
                            FROM (
                                SELECT us.url
                                FROM user_secret_images us
                                WHERE us.user_id = u.id AND us.use_yn = TRUE
                                ORDER BY us.index
                            ) t
                        ) AS secretImages,

                        -- block list
                        (
                            SELECT JSON_ARRAYAGG(ub.blocked_user_id)
                            FROM user_block_list ub
                            WHERE ub.block_user_id = u.id
                        ) AS blockUserList,
                        
                        -- 팔로워 수
                        (
                            SELECT COUNT(*)
                            FROM users_follow_list fl
                            WHERE fl.following_user_id = u.id
                        ) AS followerCount,
                        
                        -- 팔로잉 수
                        (
                            SELECT COUNT(*)
                            FROM users_follow_list fl
                            WHERE fl.follower_user_id = u.id
                        ) AS followingCount

                    FROM users u
                    WHERE u.id = %s AND u.leaved = FALSE
                    LIMIT 1;
                    """,
                    (user_id,),
                )

                row = await cur.fetchone()
                if not row:
                    return None

                columns = [col[0] for col in cur.description]
                row_dict = dict(zip(columns, row))
                return UserDetailViewRow(**row_dict)

    async def fetch_push_status(self, user_no: int):
        """
        유저 push목록과 상태 가져오기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT 1 FROM push_user_log WHERE user_no = %s AND delivery_state = 'DELIVERED' LIMIT 1",
                    (user_no,),
                )
                push_read = bool(await cur.fetchone())

                await cur.execute(
                    """
                    SELECT 1 
                    FROM push_user_log 
                    WHERE user_no = %s 
                        AND status = 'SUCCESS'
                        AND delivery_state = 'DELIVERED' 
                        AND push_type = 'profile'
                    """,
                    (user_no,),
                )
                profile_read = bool(await cur.fetchone())
                return push_read, profile_read

    async def fetch_today_ads(self, user_id: str) -> int:
        """
        유저 하루 광고 시청 횟수 가져오기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM credit_history
                    WHERE user_id = %s
                        AND description = '광고 시청 보상'
                        AND created_at >= CONVERT_TZ(CURDATE(), '+09:00', '+00:00')
                        AND created_at < CONVERT_TZ(CURDATE() + INTERVAL 1 DAY, '+09:00', '+00:00')
                    """,
                    (user_id,),
                )
                today_ad_count = await cur.fetchone()
                return today_ad_count[0] if today_ad_count else 0

    async def fetch_favorite_list(self, user_id: str) -> List[str]:
        """
        유저 즐겨찾기 리스트 가져오기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT favorite_user_id FROM users_favorite_list WHERE user_id = %s",
                    (user_id,),
                )
                favorite_list = await cur.fetchall()
                return [favorite[0] for favorite in favorite_list]

    async def check_nickname(self, nickname: str) -> bool:
        """
        유저 닉네임 중복체크하기
        """
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT 1 FROM users WHERE nickname = %s", (nickname,)
                    )
                    result = await cur.fetchone()
                    return result is not None
        except Exception as e:
            raise HTTPException(status_code=500, detail="닉네임 중복 확인 실패")

    async def get_user_row(self, user_id: str):
        """
        유저 히스토리 테이블에 기록할 정보 가져오기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                user_row = await cur.fetchone()
                columns = [col[0] for col in cur.description] if cur.description else []
                return user_row, columns

    async def insert_user_history(self, user_row, columns):
        """
        유저 히스토리 테이블에 기록
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                placeholders = ", ".join(["%s"] * len(columns))
                columns_sql = ", ".join(columns)
                insert_sql = (
                    f"INSERT INTO users_history ({columns_sql}) VALUES ({placeholders})"
                )
                await cur.execute(insert_sql, user_row)
                await conn.commit()

    async def update_user_nickname(self, user_id: str, nickname: str):
        """
        유저 닉네임 변경
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE users SET nickname = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (nickname, user_id),
                )
                await conn.commit()

    async def update_user_hashtags(self, user_id: str, hashtags_json: str):
        """
        유저 해시태그 변경
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        "UPDATE users SET hashtags = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                        (hashtags_json, user_id),
                    )
                    await conn.commit()
                except Exception as e:
                    await conn.rollback()
                    raise HTTPException(status_code=500, detail="해시태그 수정 실패")

    async def update_user_info(
        self, user_id: str, age: int, height: int, weight: int, country: str
    ):
        """
        유저 정보 변경(나이, 키, 몸무게, 나라)
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        """
                        UPDATE users
                        SET age = %s, height = %s, weight = %s, country = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (age, height, weight, country, user_id),
                    )
                    await conn.commit()
                except Exception as e:
                    await conn.rollback()
                    raise HTTPException(status_code=500, detail="사용자 정보 수정 실패")

    async def update_user_fcm(self, user_id: str, fcm: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        """
                        UPDATE users
                        SET fcm = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s AND leaved = FALSE
                        """,
                        (fcm, user_id),
                    )
                    await cur.execute(
                        """
                        UPDATE biz_account
                        SET fcm = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s AND leaved = FALSE
                        """,
                        (fcm, user_id),
                    )
                    await conn.commit()
                    return True
                except Exception:
                    await conn.rollback()
                    raise HTTPException(status_code=500, detail="FCM 수정 실패")

    async def update_user_relation(self, user_id: str, relation: str):
        """
        유저 선호 관계 변경
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        """
                        UPDATE users
                        SET relation = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (relation, user_id),
                    )
                    await conn.commit()
                except Exception:
                    await conn.rollback()
                    raise HTTPException(status_code=500, detail="관계 수정 실패")

    async def update_user_position(self, user_id: str, position: str):
        """
        유저 포지션 변경
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        """
                        UPDATE users
                        SET position = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (position, user_id),
                    )
                    await conn.commit()
                except Exception:
                    await conn.rollback()
                    raise HTTPException(status_code=500, detail="포지션 수정 실패")

    async def update_user_talk_style(self, user_id: str, talk_style: str):
        """
        유저 소통 스타일 변경
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        """
                        UPDATE users
                        SET talk_style = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (talk_style, user_id),
                    )
                    await conn.commit()
                except Exception:
                    await conn.rollback()
                    raise HTTPException(status_code=500, detail="대화 스타일 수정 실패")

    async def update_user_alarm(self, user_id: str, alarm_type: str, value: bool):
        """
        유저 알람 설정 변경
        """
        column_map = {
            "marketing_agree": "marketing_agree",  # 마케팅 수신 동의 알람
            "night_agree": "night_agree",  # 야간 수신 동의 알람
            "feed_like_agree": "feed_like_alarm_agree",  # 피드 좋아요 알람
            "feed_comment_agree": "feed_comment_alarm_agree",  # 피드 댓글 알람
            "secret_agree": "secret_alarm_agree",  # 시크릿 피드 조회 알람
            "profile_agree": "profile_alarm_agree",  # 프로필 조회 알람
            "personal_chat": "personal_chat_alarm_agree",  # 1:1 채팅 알람
            "group_chat": "group_chat_alarm_agree",  # 그룹 채팅 알람
            "post_like": "post_like_alarm_agree",  # 게시물 좋아요 알람
            "post_comment": "post_comment_alarm_agree",  # 게시물 댓글 알람
        }

        if alarm_type not in column_map:
            raise HTTPException(status_code=400, detail="Invalid alarm type")

        column_name = column_map[alarm_type]

        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:

                # users 테이블 확인
                await cur.execute(
                    "SELECT 1 FROM users WHERE id = %s AND leaved = FALSE",
                    (user_id,),
                )
                exists_user = await cur.fetchone()

                # biz_account 테이블 확인
                await cur.execute(
                    "SELECT 1 FROM biz_account WHERE id = %s AND leaved = FALSE",
                    (user_id,),
                )
                exists_biz = await cur.fetchone()

                if exists_user:
                    target_table = "users"
                elif exists_biz:
                    target_table = "biz_account"
                else:
                    raise HTTPException(
                        status_code=404, detail="존재하지 않는 계정입니다."
                    )

                try:
                    query = f"""
                        UPDATE {target_table}
                        SET {column_name} = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """

                    await cur.execute(query, (value, user_id))
                    await conn.commit()

                except Exception as e:
                    await conn.rollback()
                    raise HTTPException(status_code=500, detail="알람 설정 수정 실패")

    async def update_user_self_introduction(
        self, user_id: str, user_self_introduction: str
    ):
        """
        유저 자기소개 변경
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        """
                        UPDATE users
                        SET self_introduction = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (user_self_introduction, user_id),
                    )
                    await conn.commit()
                except Exception:
                    await conn.rollback()
                    raise HTTPException(status_code=500, detail="자기소개 수정 실패")

    async def update_user_bdsm_type(self, user_id: str, bdsm_type: str):
        """
        유저 bdsm 선호 변경
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        """
                        UPDATE users
                        SET bdsm_type = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (bdsm_type, user_id),
                    )
                    await conn.commit()
                except Exception:
                    await conn.rollback()
                    raise HTTPException(status_code=500, detail="BDSM 타입 수정 실패")

    async def check_user_block(self, user_id: str, opponent_id: str) -> bool:
        """
        상대 유저의 유저 차단여부 확인 (내가 상대방에게 차단당했는지)
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 1
                    FROM user_block_list
                    WHERE blocked_user_id = %s AND block_user_id = %s
                    """,
                    (user_id, opponent_id),
                )
                result = await cur.fetchone()
                return result is not None

    async def block_user(self, user_id: str, target_user_id: str):
        """
        유저 차단
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        """
                        INSERT INTO user_block_list (block_user_id, blocked_user_id)
                        VALUES (%s, %s)
                        """,
                        (user_id, target_user_id),
                    )

                    await cur.execute(
                        """
                        INSERT INTO user_block_list_log (block_user_id, blocked_user_id, block_type)
                        VALUES (%s, %s, 'BLOCK')
                        """,
                        (user_id, target_user_id),
                    )

                    await cur.execute(
                        "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                        (user_id,),
                    )

                    await conn.commit()
                except Exception:
                    await conn.rollback()
                    raise HTTPException(status_code=500, detail="사용자 차단 실패")

    async def report_user(
        self, chat_id: str, report_user_id: str, reported_user_id: str, reason: str
    ):
        """
        유저 신고
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        """
                        INSERT INTO user_reports (chat_id, report_user_id, reported_user_id, reason)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (chat_id, report_user_id, reported_user_id, reason),
                    )

                    await cur.execute(
                        "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                        (report_user_id,),
                    )

                    await conn.commit()
                except Exception:
                    await conn.rollback()
                    raise HTTPException(status_code=500, detail="유저 신고 실패")

    async def fetch_profile_images(self, user_id: str) -> List[str]:
        """
        유저의 프로필 이미지 가져오기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT url
                    FROM user_images
                    WHERE user_id = %s AND use_yn = TRUE
                    ORDER BY `index`
                    """,
                    (user_id,),
                )
                image_rows = await cur.fetchall()
                profile_image_urls = [url for (url,) in image_rows]
                return profile_image_urls

    async def fetch_user_block_list(self, user_id: str) -> List[str]:
        """
        유저가 차단한 유저 목록 가져오기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT blocked_user_id FROM user_block_list WHERE block_user_id = %s",
                    (user_id,),
                )
                block_rows = await cur.fetchall()
                blocked_user_ids = [
                    blocked_user_id for (blocked_user_id,) in block_rows
                ]
                return blocked_user_ids

    async def fetch_secret_images(self, user_id: str) -> List[str]:
        """
        유저의 시크릿 이미지 가져오기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT url
                    FROM user_secret_images
                    WHERE user_id = %s AND use_yn = TRUE
                    ORDER BY `index`
                    """,
                    (user_id,),
                )
                secret_rows = await cur.fetchall()
                secret_image_urls = [url for (url,) in secret_rows]
                return secret_image_urls

    async def fetch_total_view_count(self, user_id: str, viewer_id: str) -> int:
        """
        나를 본 모든 상대 유저의 총 뷰카운트 가져오기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT view_count
                    FROM users_profile_view
                    WHERE user_id = %s AND viewer_id = %s
                    """,
                    (viewer_id, user_id),
                )
                view_count_row = await cur.fetchone()
                total_view_count = view_count_row[0] if view_count_row else 0
                return total_view_count

    async def fetch_today_view_count(self, user_id: str, viewer_id: str) -> int:
        """
        나를 본 모든 상대 유저의 오늘 뷰카운트 가져오기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM users_profile_view_log
                    WHERE user_id = %s AND viewer_id = %s
                        AND created_at >= CONVERT_TZ(CURDATE(), '+09:00', '+00:00')
                        AND created_at < CONVERT_TZ(CURDATE() + INTERVAL 1 DAY, '+09:00', '+00:00')
                    """,
                    (viewer_id, user_id),
                )
                today_view_count_row = await cur.fetchone()
                today_view_count = (
                    today_view_count_row[0] if today_view_count_row else 0
                )
                return today_view_count

    async def fetch_user_list(self, user_id_list: List[str], viewer_id: str):
        if not user_id_list:
            return []

        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                placeholders = ", ".join(["%s"] * len(user_id_list))

                query = f"""
                    SELECT 
                        u.id,
                        u.fcm,
                        u.nickname,
                        u.birthday,
                        u.age,
                        u.height,
                        u.weight,
                        u.relation,
                        u.position,
                        u.country,
                        u.hashtags,
                        u.self_introduction,
                        u.bdsm_type,
                        u.leaved,
                        u.talk_style,
                        u.secret_yn,
                        u.personal_chat_alarm_agree,
                        u.group_chat_alarm_agree,
                        u.post_comment_alarm_agree,
                        u.post_like_alarm_agree,
                        u.last_connected_at,
                        u.latitude,
                        u.longitude,
                        GROUP_CONCAT(DISTINCT ui.url ORDER BY ui.`index` SEPARATOR ',') AS profileImages,
                        GROUP_CONCAT(DISTINCT si.url ORDER BY si.`index` SEPARATOR ',') AS secretImages,
                        GROUP_CONCAT(DISTINCT ubl.blocked_user_id SEPARATOR ',') AS blockUserList,
                        CASE 
                            WHEN EXISTS (
                                SELECT 1 
                                FROM user_block_list b 
                                WHERE b.block_user_id = u.id 
                                AND b.blocked_user_id = %s
                            ) THEN TRUE 
                            ELSE FALSE 
                        END AS isBlocked,
                        
                        -- 팔로워 수
                        (
                            SELECT COUNT(*)
                            FROM users_follow_list fl
                            WHERE fl.following_user_id = u.id
                        ) AS followerCount,
                        
                        -- 팔로잉 수
                        (
                            SELECT COUNT(*)
                            FROM users_follow_list fl
                            WHERE fl.follower_user_id = u.id
                        ) AS followingCount

                    FROM users u
                    LEFT JOIN user_images ui 
                        ON ui.user_id = u.id AND ui.use_yn = TRUE
                    LEFT JOIN user_secret_images si 
                        ON si.user_id = u.id AND si.use_yn = TRUE
                    LEFT JOIN user_block_list ubl 
                        ON ubl.block_user_id = u.id
                    WHERE u.id IN ({placeholders})
                        AND u.leaved = FALSE
                        AND NOT EXISTS (
                            SELECT 1 
                            FROM user_block_list bx
                            WHERE bx.block_user_id = %s 
                            AND bx.blocked_user_id = u.id
                        )
                        AND NOT EXISTS (
                            SELECT 1
                            FROM user_block_list by2
                            WHERE by2.block_user_id = u.id
                            AND by2.blocked_user_id = %s
                        )
                    GROUP BY u.id
                    ORDER BY FIELD(u.id, {placeholders})
                """

                params = (
                    [viewer_id]  # isBlocked용
                    + user_id_list  # IN (...)
                    + [viewer_id]
                    + [viewer_id]
                    + user_id_list  # ORDER BY FIELD(...)
                )

                await cur.execute(query, params)
                rows = await cur.fetchall()
                columns = [col[0] for col in cur.description]
                results = []
                for row in rows:
                    data = dict(zip(columns, row))

                    # 문자열 필드를 리스트로 변환
                    data["profileImages"] = (
                        data["profileImages"].split(",")
                        if data["profileImages"]
                        else []
                    )
                    data["secretImages"] = (
                        data["secretImages"].split(",") if data["secretImages"] else []
                    )
                    data["blockUserList"] = (
                        data["blockUserList"].split(",")
                        if data["blockUserList"]
                        else []
                    )

                    results.append(UserListRow(**data))
                return results

    async def fetch_user_id_list(
        self,
        user_id: str,
        position: str,
        relation: str,
        bdsm_type: str,
        talk_style: str,
        age: str,
        secret: bool,
    ) -> List[str]:
        """
        필터를 적용한 유저의 목록 가져오기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                # 문자열 파싱
                position = [p.strip() for p in position.split(",")] if position else []
                relation = [r.strip() for r in relation.split(",")] if relation else []
                bdsm_type = (
                    [b.strip() for b in bdsm_type.split(",")] if bdsm_type else []
                )
                talk_style = (
                    [t.strip() for t in talk_style.split(",")] if talk_style else []
                )
                age = [a.strip() for a in age.split(",")] if age else []

                query = """
                    SELECT id
                    FROM users
                    WHERE leaved = FALSE
                """
                # query문을 execute하기 위한 arguments와 필터링을 수행할 filters 리스트
                filters, arguments = [], []

                # position이 존재한다면, FIND_IN_SET을 사용한 position 필터링
                if position:
                    filters.append(
                        "("
                        + " OR ".join(["FIND_IN_SET(%s, position)"] * len(position))
                        + ")"
                    )
                    # position이 여러개일 경우 OR 조건인 한 문장으로 filters에 추가
                    # 예: FIND_IN_SET(%s, position) OR FIND_IN_SET(%s, position)
                    arguments.extend(position)

                if relation:
                    filters.append(
                        "("
                        + " OR ".join(["FIND_IN_SET(%s, relation)"] * len(relation))
                        + ")"
                    )
                    arguments.extend(relation)

                if talk_style:
                    filters.append(
                        "(" + " OR ".join(["talk_style = %s"] * len(talk_style)) + ")"
                    )
                    arguments.extend(talk_style)

                if bdsm_type:
                    filters.append(
                        "("
                        + " OR ".join(["FIND_IN_SET(%s, bdsm_type)"] * len(bdsm_type))
                        + ")"
                    )
                    arguments.extend(bdsm_type)

                if len(age) == 2:
                    filters.append(
                        """
                        TIMESTAMPDIFF(
                            YEAR,
                            STR_TO_DATE(birthday, '%%Y%%m%%d'),
                            CURDATE()
                        ) BETWEEN %s AND %s
                    """
                    )
                    arguments.extend(age)

                if secret is not None:
                    secret_exists = "EXISTS" if secret else "NOT EXISTS"
                    query_template = """
                        {secret_exists} (
                            SELECT 1 
                            FROM user_secret_images si 
                            WHERE si.user_id = users.id 
                            AND si.use_yn = TRUE
                        )
                    """
                    filters.append(query_template.format(secret_exists=secret_exists))

                if user_id:
                    filters.append(
                        """
                        NOT EXISTS (
                            SELECT 1 FROM user_block_list ubl
                            WHERE 
                                (ubl.block_user_id = %s AND ubl.blocked_user_id = users.id)
                                OR (ubl.block_user_id = users.id AND ubl.blocked_user_id = %s)
                        )
                        """
                    )
                    arguments.extend([user_id, user_id])

                if filters:
                    query += " AND " + " AND ".join(filters)

                await cur.execute(query, arguments)
                rows = await cur.fetchall()
                return [row[0] for row in rows]

    # TODOTODO
    async def fetch_near_user_id_list(
        self,
        user_id: str,
        position: str,
        relation: str,
        bdsm_type: str,
        talk_style: str,
        age: str,
        secret: bool,
    ) -> List[str]:
        """
        필터를 적용한 유저의 목록 중
        1) 위치 있는 유저는 거리순 정렬
        2) 위치 없는 유저는 나중에 append
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                # 내 위치 정보 조회
                await cur.execute(
                    "SELECT latitude, longitude FROM users WHERE id = %s AND leaved = FALSE",
                    (user_id,),
                )
                location = await cur.fetchone()
                if not location:
                    raise HTTPException(
                        status_code=404, detail="탈퇴하거나 존재하지 않는 사용자입니다."
                    )

                lat, lng = location

                # 문자열 파싱
                position = [p.strip() for p in position.split(",")] if position else []
                relation = [r.strip() for r in relation.split(",")] if relation else []
                bdsm_type = (
                    [b.strip() for b in bdsm_type.split(",")] if bdsm_type else []
                )
                talk_style = (
                    [t.strip() for t in talk_style.split(",")] if talk_style else []
                )
                age = [a.strip() for a in age.split(",")] if age else []

                query = """
                    SELECT id
                    FROM users
                    WHERE leaved = FALSE
                      AND latitude IS NOT NULL
                      AND longitude IS NOT NULL
                      AND id != %s
                """
                filters, arguments = [], [user_id]

                if position:
                    filters.append(
                        "("
                        + " OR ".join(["FIND_IN_SET(%s, position)"] * len(position))
                        + ")"
                    )
                    arguments.extend(position)

                if relation:
                    filters.append(
                        "("
                        + " OR ".join(["FIND_IN_SET(%s, relation)"] * len(relation))
                        + ")"
                    )
                    arguments.extend(relation)

                if talk_style:
                    filters.append(
                        "("
                        + " OR ".join(["FIND_IN_SET(%s, talk_style)"] * len(talk_style))
                        + ")"
                    )
                    arguments.extend(talk_style)

                if bdsm_type:
                    filters.append(
                        "("
                        + " OR ".join(["FIND_IN_SET(%s, bdsm_type)"] * len(bdsm_type))
                        + ")"
                    )
                    arguments.extend(bdsm_type)

                if len(age) == 2:
                    filters.append(
                        """
                        TIMESTAMPDIFF(
                            YEAR,
                            STR_TO_DATE(birthday, '%%Y%%m%%d'),
                            CURDATE()
                        ) BETWEEN %s AND %s
                        """
                    )
                    arguments.extend(age)

                if secret is not None:
                    secret_exists = "EXISTS" if secret else "NOT EXISTS"
                    query_template = f"""
                        {secret_exists} (
                            SELECT 1 
                            FROM user_secret_images si 
                            WHERE si.user_id = users.id 
                            AND si.use_yn = TRUE
                        )
                    """
                    filters.append(query_template)

                if user_id:
                    filters.append(
                        """
                        NOT EXISTS (
                            SELECT 1 FROM user_block_list ubl
                            WHERE 
                                (ubl.block_user_id = %s AND ubl.blocked_user_id = users.id)
                                OR (ubl.block_user_id = users.id AND ubl.blocked_user_id = %s)
                        )
                        """
                    )
                    arguments.extend([user_id, user_id])

                if filters:
                    query += " AND " + " AND ".join(filters)

                # 거리순 정렬 추가
                query += f"""
                    ORDER BY (6371 * acos(
                        cos(radians({lat})) * cos(radians(latitude)) *
                        cos(radians(longitude) - radians({lng})) +
                        sin(radians({lat})) * sin(radians(latitude))
                    ))
                """

                await cur.execute(query, arguments)
                near_rows = [row[0] for row in await cur.fetchall()]

                null_query = """
                    SELECT id
                    FROM users
                    WHERE leaved = FALSE
                      AND (latitude IS NULL OR longitude IS NULL)
                      AND id != %s
                """
                null_args = [user_id]

                if filters:
                    null_query += " AND " + " AND ".join(filters)
                    null_args.extend(arguments[1:])  # filters 인자 재활용

                await cur.execute(null_query, null_args)
                null_rows = [row[0] for row in await cur.fetchall()]

                return near_rows + null_rows

    # TODO
    async def fetch_nearby_user_list(
        self,
        user_id: str,
        page: int,
        age: str,
        position: str,
        relation: str,
        bdsm_type: str,
        talk_style: str,
        secret: bool,
    ) -> List[str]:
        offset = (page - 1) * 30

        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                # 내 위치 조회
                await cur.execute(
                    "SELECT latitude, longitude FROM users WHERE id = %s AND leaved = FALSE",
                    (user_id,),
                )
                location = await cur.fetchone()
                if not location:
                    raise HTTPException(
                        status_code=404, detail="탈퇴하거나 존재하지 않는 사용자입니다."
                    )

                lat, lng = location

                # 문자열 파싱
                position = [p.strip() for p in position.split(",")] if position else []
                relation = [r.strip() for r in relation.split(",")] if relation else []
                bdsm_type = (
                    [b.strip() for b in bdsm_type.split(",")] if bdsm_type else []
                )
                talk_style = (
                    [t.strip() for t in talk_style.split(",")] if talk_style else []
                )
                age = [a.strip() for a in age.split(",")] if age else []

                query = """
                    SELECT
                        id,
                        (6371 * acos(
                            cos(radians(%s)) * cos(radians(latitude)) *
                            cos(radians(longitude) - radians(%s)) +
                            sin(radians(%s)) * sin(radians(latitude))
                        )) AS distance
                    FROM users
                    WHERE leaved = FALSE
                    AND id != %s
                """
                arguments = [lat, lng, lat, user_id]
                filters = []

                if position:
                    filters.append(
                        "("
                        + " OR ".join(["FIND_IN_SET(%s, position)"] * len(position))
                        + ")"
                    )
                    arguments.extend(position)
                if relation:
                    filters.append(
                        "("
                        + " OR ".join(["FIND_IN_SET(%s, relation)"] * len(relation))
                        + ")"
                    )
                    arguments.extend(relation)
                if talk_style:
                    filters.append(
                        "("
                        + " OR ".join(["FIND_IN_SET(%s, talk_style)"] * len(talk_style))
                        + ")"
                    )
                    arguments.extend(talk_style)
                if bdsm_type:
                    filters.append(
                        "("
                        + " OR ".join(["FIND_IN_SET(%s, bdsm_type)"] * len(bdsm_type))
                        + ")"
                    )
                    arguments.extend(bdsm_type)
                if len(age) == 2:
                    filters.append(
                        """
                        TIMESTAMPDIFF(
                            YEAR,
                            STR_TO_DATE(birthday, '%%Y%%m%%d'),
                            CURDATE()
                        ) BETWEEN %s AND %s
                        """
                    )
                    arguments.extend(age)
                if secret is not None:
                    secret_exists = "EXISTS" if secret else "NOT EXISTS"
                    filters.append(
                        f"""
                        {secret_exists} (
                            SELECT 1
                            FROM user_secret_images si
                            WHERE si.user_id = users.id
                            AND si.use_yn = TRUE
                        )
                        """
                    )
                filters.append(
                    """
                    NOT EXISTS (
                        SELECT 1 FROM user_block_list ubl
                        WHERE
                            (ubl.block_user_id = %s AND ubl.blocked_user_id = users.id)
                            OR (ubl.block_user_id = users.id AND ubl.blocked_user_id = %s)
                    )
                    """
                )
                arguments.extend([user_id, user_id])

                if filters:
                    query += " AND " + " AND ".join(filters)

                query += """
                    ORDER BY
                        (latitude IS NULL OR longitude IS NULL),
                        distance ASC
                    LIMIT %s OFFSET %s
                """
                arguments.extend([30, offset])
                await cur.execute(query, arguments)
                rows = await cur.fetchall()
                return [row[0] for row in rows]

    async def fetch_user_fcm_list(self, user_id_list: List[str]) -> List[str]:
        """
        유저들의 fcm리스트를 가져오기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                if not user_id_list:
                    return []

                placeholders = ", ".join(["%s"] * len(user_id_list))
                query_template = """
                    SELECT id, fcm
                    FROM users
                    WHERE id IN ({placeholders}) AND leaved = FALSE
                """
                query = query_template.format(placeholders=placeholders)

                await cur.execute(query, tuple(user_id_list))
                fcm_rows = await cur.fetchall()

                # fcm이 None이 아닌 것만 필터링
                fcm_tokens = [fcm for (_, fcm) in fcm_rows if fcm]
                return fcm_tokens

    async def leave_user(self, user_id: str, reason: str):
        """
        유저 탈퇴
        """
        init_firebase_admin()
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        "UPDATE users SET leaved = TRUE, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                        (user_id,),
                    )

                    await cur.execute(
                        "INSERT INTO leaved_users (user_id, reason) VALUES (%s, %s)",
                        (user_id, reason),
                    )

                    await conn.commit()
                    # Firebase Authentication에서 사용자 삭제
                    try:
                        auth.delete_user(user_id)
                        logger.info(f"Firebase user {user_id} deleted successfully.")
                    # 이미 삭제되어있는 경우
                    except auth.UserNotFoundError:
                        logger.warning(
                            f"Firebase user {user_id} not found (already deleted)."
                        )
                    # 그 외의 에러
                    except Exception as e:
                        logger.error(f"Firebase deletion failed: {e}")

                except Exception:
                    await conn.rollback()
                    raise HTTPException(status_code=500, detail="사용자 탈퇴 실패")

    # TODO
    async def user_health_check(
        self, user_id: str, latitude: Optional[float], longitude: Optional[float]
    ):
        """
        사용자의 위치를 가져오기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        """
                        UPDATE users
                        SET last_connected_at = CURRENT_TIMESTAMP,
                            latitude = %s,
                            longitude = %s
                        WHERE id = %s
                        """,
                        (latitude, longitude, user_id),
                    )
                    await conn.commit()
                except Exception:
                    await conn.rollback()
                    raise HTTPException(status_code=500, detail="유저 상태 갱신 실패")

    async def disable_images(self, cur, user_id: str, urls: List[str]):
        """
        유저 이미지 사용안함 처리하기
        """
        for url in urls:
            await cur.execute(
                """
                UPDATE user_images
                SET use_yn = FALSE
                WHERE user_id = %s AND url = %s
                """,
                (user_id, url),
            )

    async def update_image_order(self, cur, user_id: str, urls: List[str]):
        """
        유저의 이미지 순서를 조정하기
        """
        for idx, url in enumerate(urls):
            await cur.execute(
                """
                UPDATE user_images
                SET `index` = %s
                WHERE user_id = %s AND url = %s
                """,
                (idx, user_id, url),
            )

    async def update_user_timestamp(self, cur, user_id: str):
        """
        유저의 updated_at을 업데이트하기
        """
        await cur.execute(
            "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (user_id,),
        )

    # 기존 히스토리 추가에서, 유저 이미지 리스트를 넣기 위한 로직인데, 수정 필요.
    async def insert_user_history_with_images(
        self, cur, user_id: str, image_urls: List[str]
    ):
        """
        유저 이미지가 변경되었을때, 유저 히스토리 테이블에 기록.
        """
        await cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user_row = await cur.fetchone()
        columns = [col[0] for col in cur.description] if cur.description else []

        if not user_row:
            return

        columns.append("image_list")
        user_row = list(user_row) + [",".join(image_urls)]

        placeholders = ", ".join(["%s"] * len(columns))
        columns_sql = ", ".join(columns)

        query_template = """
        INSERT INTO users_history ({columns_sql})
        VALUES ({placeholders})
        """
        insert_history = query_template.format(
            columns_sql=columns_sql, placeholders=placeholders
        )

        await cur.execute(insert_history, user_row)

    async def update_user_images(
        self,
        user_id: str,
        keep_images: list[str],
        remove_images: list[str],
        uploaded_urls: list[str],
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await conn.begin()
                try:
                    if remove_images:
                        for url in remove_images:
                            await cur.execute(
                                """
                                UPDATE user_images
                                SET use_yn = FALSE
                                WHERE user_id = %s AND url = %s
                                """,
                                (user_id, url),
                            )

                    for idx, url in enumerate(keep_images):
                        await cur.execute(
                            """
                            UPDATE user_images
                            SET `index` = %s
                            WHERE user_id = %s AND url = %s
                            """,
                            (idx, user_id, url),
                        )

                    start_index = len(keep_images)
                    for idx, image_url in enumerate(uploaded_urls, start=start_index):
                        await cur.execute(
                            """
                            INSERT INTO user_images (user_id, `index`, url, use_yn)
                            VALUES (%s, %s, %s, TRUE)
                            """,
                            (user_id, idx, image_url),
                        )

                    await cur.execute(
                        """
                        UPDATE users
                        SET updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (user_id,),
                    )

                    await conn.commit()

                except Exception as e:
                    await conn.rollback()
                    raise HTTPException(
                        status_code=500,
                        detail=f"DB 업데이트 실패: {e}",
                    )

        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT url
                    FROM user_images
                    WHERE user_id = %s AND use_yn = TRUE
                    ORDER BY `index` ASC
                    """,
                    (user_id,),
                )
                rows = await cur.fetchall()
                return [row[0] for row in rows]

    async def fetch_user_fcm(self, user_id: str) -> str:
        """
        유저의 fcm 코드를 가져오기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT fcm
                    FROM users
                    WHERE id = %s
                        AND leaved = FALSE
                        AND fcm IS NOT NULL
                    LIMIT 1
                    """,
                    (user_id,),
                )
                result = await cur.fetchone()
                return result[0] if result else None

    async def fetch_user_nickname(self, user_id: str) -> str:
        """
        유저의 닉네임을 가져오기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT nickname
                    FROM users
                    WHERE id = %s
                        AND leaved = FALSE
                    LIMIT 1
                    """,
                    (user_id,),
                )
                result = await cur.fetchone()
                return result[0] if result else None

    async def fetch_user_no(self, user_id: str) -> int:
        """
        유저의 user_no를 가져오기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT user_no
                    FROM users
                    WHERE id = %s
                        AND leaved = FALSE
                    LIMIT 1
                    """,
                    (user_id,),
                )
                result = await cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="User not found")
                return result[0]

    async def fetch_push_user_logs(
        self, user_no: int, push_type: Optional[str], page: int
    ) -> List[tuple]:
        """
        유저의 푸시 로그를 가져오기, 20개씩 페이지네이션.
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                offset = (page - 1) * 20
                if push_type == "userAction":
                    await cur.execute(
                        """
                        SELECT token, payload, delivered_at, opened_at
                        FROM push_user_log
                        WHERE user_no = %s
                          AND status IN ('SUCCESS', 'OPENED')
                          AND push_type IN ('profile', 'postLike', 'postComment', 'secret', 'feedLike', 'feedComment', 'secretFeedComment', 'secretFeedLike')
                        ORDER BY delivered_at DESC
                        LIMIT 20 OFFSET %s
                        """,
                        (user_no, offset),
                    )

                elif push_type:
                    await cur.execute(
                        """
                        SELECT token, payload, delivered_at, opened_at
                        FROM push_user_log
                        WHERE user_no = %s
                          AND status IN ('SUCCESS', 'OPENED')
                          AND push_type = %s
                        ORDER BY delivered_at DESC
                        LIMIT 20 OFFSET %s
                        """,
                        (user_no, push_type, offset),
                    )

                else:
                    await cur.execute(
                        """
                        SELECT token, payload, delivered_at, opened_at
                        FROM push_user_log
                        WHERE user_no = %s
                          AND status = 'SUCCESS'
                        ORDER BY delivered_at DESC
                        LIMIT 20 OFFSET %s
                        """,
                        (user_no, offset),
                    )

                rows = await cur.fetchall()
                return rows or []

    async def update_push_opened_state(self, user_no: int, push_id: str) -> bool:
        """
        유저의 푸시를 읽음처리하기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE push_user_log
                    SET delivery_state = 'OPENED',
                        opened_at = CURRENT_TIMESTAMP
                    WHERE user_no = %s
                      AND push_id = %s
                      AND status = 'SUCCESS'
                    """,
                    (user_no, push_id),
                )

                await conn.commit()
                # 실제로 업데이트 되었는지 확인하기.
                return cur.rowcount > 0

    async def update_all_push_opened_state(self, user_no: int) -> bool:
        """
        유저의 모든 푸시를 읽음처리하기.
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE push_user_log
                    SET delivery_state = 'OPENED',
                        opened_at = CURRENT_TIMESTAMP
                    WHERE user_no = %s
                      AND status = 'SUCCESS'
                      AND delivery_state != 'OPENED'
                    """,
                    (user_no,),
                )
                await conn.commit()
                return cur.rowcount > 0

    async def check_user_block(self, user_id: str, target_user_id: str) -> bool:
        """
        상대 유저의 유저 차단여부 확인 (내가 상대방에게 차단당했는지)
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 1
                    FROM user_block_list
                    WHERE blocked_user_id = %s AND block_user_id = %s
                    """,
                    (user_id, target_user_id),
                )
                result = await cur.fetchone()
                return result is not None

    async def insert_user_profile_view(self, user_id: str, viewer_id: str) -> None:
        """
        상대 유저의 프로필을 조회시, db에 기록
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        """
                        SELECT 1
                        FROM users_profile_view
                        WHERE user_id = %s AND viewer_id = %s
                        """,
                        (user_id, viewer_id),
                    )
                    is_viewed = await cur.fetchone()

                    if is_viewed:
                        await cur.execute(
                            """
                            UPDATE users_profile_view
                            SET view_count = view_count + 1,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE user_id = %s AND viewer_id = %s
                            """,
                            (user_id, viewer_id),
                        )

                    else:
                        await cur.execute(
                            """
                            INSERT INTO users_profile_view (user_id, viewer_id, type, created_at, view_count)
                            VALUES (%s, %s, 'view', CURRENT_TIMESTAMP, 1)
                            """,
                            (user_id, viewer_id),
                        )

                    await cur.execute(
                        """
                        INSERT INTO users_profile_view_log (user_id, viewer_id, created_at)
                        VALUES (%s, %s, CURRENT_TIMESTAMP)
                        """,
                        (user_id, viewer_id),
                    )

                    await conn.commit()
                except Exception:
                    await conn.rollback()
                    raise

    async def fetch_user_profile_view(self, page: int, user_id: str) -> list[dict]:
        """
        내 프로필을 조회한 사람 가져오기
        """
        offset = (page - 1) * 20
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT upv.viewer_id AS id,
                           upv.updated_at AS viewedAt,
                           upv.view_count AS viewCount,
                           COALESCE(today_views.today_count, 0) AS todayViewCount
                    FROM users_profile_view upv
                    JOIN users u
                        ON upv.viewer_id = u.id
                    LEFT JOIN (
                        SELECT user_id, viewer_id, COUNT(*) AS today_count
                        FROM users_profile_view_log
                        WHERE created_at >= CONVERT_TZ(CURDATE(), '+09:00', '+00:00')
                          AND created_at <  CONVERT_TZ(CURDATE() + INTERVAL 1 DAY, '+09:00', '+00:00')
                        GROUP BY user_id, viewer_id
                    ) today_views
                        ON upv.user_id = today_views.user_id
                        AND upv.viewer_id = today_views.viewer_id
                    WHERE upv.user_id = %s
                      AND upv.updated_at >= DATE_SUB(CURRENT_TIMESTAMP, INTERVAL 1 YEAR)
                      AND u.leaved = FALSE
                      AND NOT EXISTS (
                            SELECT 1
                            FROM user_block_list ubl
                            WHERE ubl.block_user_id = %s
                              AND ubl.blocked_user_id = upv.viewer_id
                      )
                      AND NOT EXISTS (
                            SELECT 1
                            FROM user_block_list ubl2
                            WHERE ubl2.block_user_id = upv.viewer_id
                                AND ubl2.blocked_user_id = %s
                      )
                    ORDER BY upv.updated_at DESC
                    LIMIT 20 OFFSET %s
                    """,
                    (user_id, user_id, user_id, offset),
                )

                rows = await cur.fetchall()
                columns = [col[0] for col in cur.description]
                return [ProfileViewRow(**dict(zip(columns, row))) for row in rows]

    async def mark_profile_push_read(self, user_no: int) -> None:
        """
        프로필 푸시를 읽음처리하기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE push_user_log
                    SET delivery_state = 'OPENED',
                        opened_at = CURRENT_TIMESTAMP
                    WHERE user_no = %s
                      AND push_type = 'profile'
                      AND status = 'SUCCESS'
                      AND delivery_state = 'DELIVERED'
                    """,
                    (user_no,),
                )
                await conn.commit()

    async def insert_user_secret_images_view(
        self, viewer_id: str, target_user_id: str
    ) -> None:
        """
        상대방의 시크릿 이미지를 조회할때, db에 기록
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        """
                        SELECT 1
                        FROM users_secret_view
                        WHERE user_id = %s AND viewer_id = %s
                        """,
                        (target_user_id, viewer_id),
                    )
                    is_viewed = await cur.fetchone()
                    if is_viewed:
                        await cur.execute(
                            """
                            UPDATE users_secret_view
                            SET view_count = view_count + 1,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE user_id = %s AND viewer_id = %s
                            """,
                            (target_user_id, viewer_id),
                        )
                    else:
                        await cur.execute(
                            """
                            INSERT INTO users_secret_view (user_id, viewer_id, type, created_at, view_count)
                            VALUES (%s, %s, 'view', CURRENT_TIMESTAMP, 1)
                            """,
                            (target_user_id, viewer_id),
                        )

                    await cur.execute(
                        """
                        INSERT INTO users_secret_view_log (user_id, viewer_id, created_at)
                        VALUES (%s, %s, CURRENT_TIMESTAMP)
                        """,
                        (target_user_id, viewer_id),
                    )

                    await conn.commit()
                except Exception:
                    await conn.rollback()
                    raise

    async def fetch_user_secret_list(self, page: int, user_id: str) -> list[dict]:
        """
        유저의 시크릿 앨범을 조회한 사람들 목록 가져오기
        """
        offset = (page - 1) * 20
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT usv.viewer_id AS viewerId,
                           usv.updated_at AS viewedAt,
                           upv.view_count AS viewCount,
                           COALESCE(today_views.today_count, 0) AS todayViewCount
                    FROM users_secret_view usv
                    JOIN users u
                        ON usv.viewer_id = u.id
                    LEFT JOIN user_block_list ubl
                        ON usv.user_id = ubl.block_user_id
                        AND usv.viewer_id = ubl.blocked_user_id
                    LEFT JOIN users_profile_view upv
                        ON usv.user_id = upv.user_id
                        AND usv.viewer_id = upv.viewer_id
                    LEFT JOIN (
                        SELECT user_id, viewer_id, COUNT(*) AS today_count
                        FROM users_profile_view_log
                        WHERE created_at >= CONVERT_TZ(CURDATE(), '+09:00', '+00:00')
                          AND created_at <  CONVERT_TZ(CURDATE() + INTERVAL 1 DAY, '+09:00', '+00:00')
                        GROUP BY user_id, viewer_id
                    ) today_views
                        ON usv.user_id = today_views.user_id
                        AND usv.viewer_id = today_views.viewer_id
                    WHERE usv.user_id = %s
                      AND usv.updated_at >= DATE_SUB(CURRENT_TIMESTAMP, INTERVAL 1 YEAR)
                      AND u.leaved = FALSE
                      AND ubl.id IS NULL
                    ORDER BY usv.updated_at DESC
                    LIMIT 20 OFFSET %s
                    """,
                    (user_id, offset),
                )

                rows = await cur.fetchall()
                columns = [col[0] for col in cur.description]
                return [ViewCountRow(**dict(zip(columns, row))) for row in rows]

    async def mark_secret_push_as_read(self, user_no: int) -> None:
        """
        시크릿 앨범 푸시 (push_type='secret') 읽음 처리
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE push_user_log
                    SET delivery_state = 'OPENED',
                        opened_at = CURRENT_TIMESTAMP
                    WHERE user_no = %s
                      AND push_type = 'secret'
                      AND status = 'SUCCESS'
                      AND delivery_state = 'DELIVERED'
                    """,
                    (user_no,),
                )
                await conn.commit()

    async def has_secret_images(self, user_id: str) -> bool:
        """
        유저의 시크릿 앨범이 있는지 조회하기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 1
                    FROM user_secret_images
                    WHERE user_id = %s AND use_yn = TRUE
                    LIMIT 1
                    """,
                    (user_id,),
                )
                result = await cur.fetchone()
                return bool(result)

    async def has_pending_secret_request(
        self, target_user_id: str, requester_id: str
    ) -> bool:
        """
        유저의 시크릿 앨범 요청이 pending상태인지 확인하기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 1
                    FROM user_secret_requests
                    WHERE user_id = %s
                      AND request_id = %s
                      AND approve_status = 'PENDING'
                    LIMIT 1
                    """,
                    (target_user_id, requester_id),
                )
                result = await cur.fetchone()
                return bool(result)

    async def insert_secret_request(
        self, target_user_id: str, requester_id: str
    ) -> None:
        """
        유저의 시크릿 앨범 요청을 db에 기록하기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO user_secret_requests (user_id, request_id, approve_status)
                    VALUES (%s, %s, 'PENDING')
                    """,
                    (target_user_id, requester_id),
                )
                await conn.commit()

    async def fetch_secret_album_status(self, user_id: str) -> bool:
        """
        유저의 시크랫 앨범 요청 상태를 조회하기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT secret_yn
                    FROM users
                    WHERE id = %s
                      AND leaved = FALSE
                    LIMIT 1
                    """,
                    (user_id,),
                )
                result = await cur.fetchone()
                return bool(result and result[0])

    async def insert_user_credit_secret_view(
        self, user_id: str, secret_user_id: str
    ) -> None:
        """
        유저가 결제한 시크릿 앨범 db에 기록하기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO user_credit_secret_view (user_id, viewed_id, created_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    """,
                    (user_id, secret_user_id),
                )
                await conn.commit()

    async def fetch_credit_secret_view_list(
        self, page: int, user_id: str
    ) -> list[dict]:
        """
        유저가 결제한 시크릿 앨범 리스트 가져오기
        """
        offset = (page - 1) * 20
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT
                        ucsv.viewed_id,
                        MAX(ucsv.created_at) AS viewed_at
                    FROM user_credit_secret_view ucsv
                    JOIN users u
                        ON ucsv.user_id = u.id
                    WHERE ucsv.user_id = %s
                        AND u.leaved = FALSE
                        AND ucsv.created_at >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 24 HOUR)
                        AND NOT EXISTS (
                            SELECT 1
                            FROM user_block_list ubl
                            WHERE 
                                ubl.block_user_id = %s AND ubl.blocked_user_id = ucsv.viewed_id
                        )
                        AND NOT EXISTS (
                            SELECT 1
                            FROM user_block_list ubl2
                            WHERE 
                                ubl2.block_user_id = ucsv.viewed_id AND ubl2.blocked_user_id = %s
                        )
                    GROUP BY ucsv.viewed_id
                    ORDER BY viewed_at DESC
                    LIMIT 20 OFFSET %s
                    """,
                    (user_id, user_id, user_id, offset),
                )

                rows = await cur.fetchall()
                credit_secret_list = [
                    {
                        "viewedId": row[0],
                        "viewedAt": row[1].strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    for row in rows
                ]

                return credit_secret_list

    async def approve_secret_request(
        self, target_user_id: str, requester_id: str
    ) -> None:
        """
        유저의 시크릿 앨범 요청 수락하기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE user_secret_requests
                    SET approve_status = 'APPROVE'
                    WHERE request_id = %s
                      AND user_id = %s
                      AND approve_status = 'PENDING'
                    """,
                    (target_user_id, requester_id),
                )
                await conn.commit()

    async def reject_secret_request(
        self, target_user_id: str, requester_id: str
    ) -> None:
        """
        유저의 시크릿 앨범 요청 거절하기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE user_secret_requests
                    SET approve_status = 'REJECT'
                    WHERE request_id = %s
                      AND user_id = %s
                      AND approve_status = 'PENDING'
                    """,
                    (target_user_id, requester_id),
                )
                await conn.commit()

    async def fetch_my_secret_requests(self, user_id: str) -> list[UserSecretResponse]:
        """
        유저의 시크릿 앨범 요청 목록 보기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT user_id, request_id, approve_status, created_at
                    FROM user_secret_requests
                    WHERE request_id = %s
                    ORDER BY created_at DESC
                    """,
                    (user_id,),
                )
                rows = await cur.fetchall()
                return [
                    UserSecretResponse(
                        userId=r[0],
                        requestId=r[1],
                        approveStatus=r[2],
                        createdAt=r[3],
                    )
                    for r in rows
                ]

    async def fetch_opponent_secret_requests(
        self, user_id: str
    ) -> list[UserSecretResponse]:
        """
        유저에게 온 시크릿 앨범 요청 목록 보기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT user_id, request_id, approve_status, created_at
                    FROM user_secret_requests
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    """,
                    (user_id,),
                )
                rows = await cur.fetchall()
                return [
                    UserSecretResponse(
                        userId=r[0],
                        requestId=r[1],
                        approveStatus=r[2],
                        createdAt=r[3],
                    )
                    for r in rows
                ]

    async def cancel_secret_request(
        self, target_user_id: str, requester_id: str
    ) -> None:
        """
        유저의 시크릿 앨범 요청 취소하기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE user_secret_requests
                    SET approve_status = 'CANCEL'
                    WHERE request_id = %s
                      AND user_id = %s
                      AND approve_status = 'PENDING'
                    """,
                    (requester_id, target_user_id),
                )
                await conn.commit()

    async def fetch_my_secret_images(self, user_id: str) -> list[str] | None:
        """
        유저의 시크릿 이미지 조회하기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT url 
                    FROM user_secret_images
                    WHERE user_id = %s AND use_yn = TRUE
                    ORDER BY `index`
                    """,
                    (user_id,),
                )
                rows = await cur.fetchall()
                return [r[0] for r in rows] if rows else None

    async def has_approved_secret_request(
        self, user_id: str, target_user_id: str
    ) -> bool:
        """
        유저의 시크릿 앨범 요청이 수락되었는지 확인하기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 1
                    FROM user_secret_requests
                    WHERE user_id = %s
                      AND request_id = %s
                      AND approve_status = 'APPROVE'
                    """,
                    (user_id, target_user_id),
                )
                return bool(await cur.fetchone())

    async def cancel_approved_secret_request(
        self, user_id: str, target_user_id: str
    ) -> None:
        """
        유저의 시크릿 앨범 요청 수락을 취소하기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE user_secret_requests
                    SET approve_status = 'CANCEL'
                    WHERE user_id = %s
                      AND request_id = %s
                      AND approve_status = 'APPROVE'
                    """,
                    (user_id, target_user_id),
                )
                await conn.commit()

    # TODO
    async def fetch_user_credit(self, user_id: str) -> int:
        """
        유저의 고래코인 개수 조회하기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT credit FROM users WHERE id = %s AND leaved = FALSE",
                    (user_id,),
                )
                row = await cur.fetchone()
                return row[0] if row else 0

    # TODO
    async def add_user_credit(self, user_id: str, amount: int, reason: str) -> None:
        """
        유저의 고래코인 지급하기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE users
                    SET credit = credit + %s
                    WHERE id = %s
                    """,
                    (amount, user_id),
                )

                await cur.execute(
                    """
                    INSERT INTO credit_history (user_id, amount, description, created_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    """,
                    (user_id, amount, reason),
                )
                await conn.commit()

    async def deduct_user_credit(self, user_id: str, amount: int, reason: str) -> None:
        """
        유저의 고래코인 소모하기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE users
                    SET credit = credit - %s
                    WHERE id = %s
                    """,
                    (amount, user_id),
                )

                await cur.execute(
                    """
                    INSERT INTO credit_history (user_id, amount, description, created_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    """,
                    (user_id, -amount, reason),
                )
                await conn.commit()

    async def insert_credit_profile_view(self, viewer_id: str, viewed_id: str) -> None:
        """
        유저의 시크릿 프로필 조회하기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                # 중복 확인 (필요 시 추가 가능)
                await cur.execute(
                    """
                    SELECT 1
                    FROM user_credit_profile_view
                    WHERE user_id = %s AND viewed_id = %s
                    """,
                    (viewer_id, viewed_id),
                )

                # 단순히 로그는 여러 번 쌓이게 둘 수도 있음
                await cur.execute(
                    """
                    INSERT INTO user_credit_profile_view (user_id, viewed_id, created_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    """,
                    (viewer_id, viewed_id),
                )
                await conn.commit()

    async def fetch_credit_profile_view_list(
        self, user_id: str, page: int
    ) -> list[dict]:
        """
        유저가 결제한 시크릿 프로필 조회하기
        """
        offset = (page - 1) * 20
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 
                        ucpv.viewed_id AS viewerId,
                        MAX(ucpv.created_at) AS viewedAt,
                        COALESCE(upv.view_count, 0) AS viewCount,
                        COALESCE(today_views.today_count, 0) AS todayViewCount
                    FROM user_credit_profile_view ucpv
                    JOIN users u
                        ON ucpv.viewed_id = u.id
                    LEFT JOIN users_profile_view upv
                        ON upv.user_id = %s
                        AND upv.viewer_id = ucpv.viewed_id
                    LEFT JOIN (
                        SELECT user_id, viewer_id, COUNT(*) AS today_count
                        FROM users_profile_view_log
                        WHERE user_id = %s
                            AND created_at >= CONVERT_TZ(CURDATE(), '+09:00', '+00:00')
                            AND created_at <  CONVERT_TZ(CURDATE() + INTERVAL 1 DAY, '+09:00', '+00:00')
                        GROUP BY user_id, viewer_id
                    ) today_views
                        ON today_views.user_id = %s
                        AND today_views.viewer_id = ucpv.viewed_id
                    WHERE ucpv.user_id = %s
                        AND u.leaved = FALSE
                        AND NOT EXISTS (
                            SELECT 1
                            FROM user_block_list ubl
                            WHERE 
                                ubl.block_user_id = %s AND ubl.blocked_user_id = ucpv.viewed_id
                        )
                        AND NOT EXISTS (
                            SELECT 1
                            FROM user_block_list ubl2
                            WHERE 
                                ubl2.block_user_id = ucpv.viewed_id AND ubl2.blocked_user_id = %s
                        )
                    GROUP BY ucpv.viewed_id, upv.view_count, today_views.today_count
                    ORDER BY viewedAt DESC
                    LIMIT 20 OFFSET %s
                    """,
                    (user_id, user_id, user_id, user_id, user_id, user_id, offset),
                )

                rows = await cur.fetchall()
                columns = [col[0] for col in cur.description]
                return [ViewCountRow(**dict(zip(columns, row))) for row in rows]

    async def fetch_user_block_list_page(self, user_id: str, page: int) -> list[str]:
        """
        유저 차단 목록 가져오기, 20개씩 페이지네이션
        """
        offset = (page - 1) * 20
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT ubl.blocked_user_id
                    FROM user_block_list ubl
                    JOIN users u
                        ON ubl.blocked_user_id = u.id
                    WHERE ubl.block_user_id = %s
                        AND u.leaved = FALSE
                    ORDER BY ubl.created_at DESC
                    LIMIT 20 OFFSET %s
                    """,
                    (user_id, offset),
                )
                rows = await cur.fetchall()
                return [row[0] for row in rows]

    async def delete_block_user(self, user_id: str, target_user_id: str) -> None:
        """
        유저의 차단 해제하기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    DELETE FROM user_block_list
                    WHERE block_user_id = %s AND blocked_user_id = %s
                    """,
                    (user_id, target_user_id),
                )

                await cur.execute(
                    """
                    INSERT INTO user_block_list_log (block_user_id, blocked_user_id, block_type)
                    VALUES (%s, %s, 'UNBLOCK')
                    """,
                    (user_id, target_user_id),
                )
                await conn.commit()

    async def poke_user(self, user_id: str, target_user_id: str) -> None:
        """
        유저 찌르기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT pocker_id
                    FROM users_poke_list
                    WHERE pocker_id = %s AND user_id = %s
                    """,
                    (user_id, target_user_id),
                )
                is_poked = await cur.fetchone()

                if is_poked:
                    await cur.execute(
                        """
                        UPDATE users_poke_list
                        SET updated_at = CURRENT_TIMESTAMP,
                            poke_count = poke_count + 1
                        WHERE pocker_id = %s AND user_id = %s
                        """,
                        (user_id, target_user_id),
                    )
                else:
                    await cur.execute(
                        """
                        INSERT INTO users_poke_list (user_id, pocker_id, type, created_at, poke_count)
                        VALUES (%s, %s, 'poke', CURRENT_TIMESTAMP, 1)
                        """,
                        (target_user_id, user_id),
                    )

                await cur.execute(
                    """
                    INSERT INTO users_poke_list_log (user_id, pocker_id, created_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    """,
                    (user_id, target_user_id),
                )
                await conn.commit()

    async def fetch_my_poke_list(self, user_id: str, page: int) -> list[dict]:
        """
        유저의 찌르기 목록 조회하기
        """
        offset = (page - 1) * 20
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT up.pocker_id, up.updated_at, up.poke_count
                    FROM users_poke_list up
                    JOIN users u
                        ON up.pocker_id = u.id
                    LEFT JOIN user_block_list ubl
                        ON up.user_id = ubl.block_user_id
                        AND up.pocker_id = ubl.blocked_user_id
                    WHERE up.user_id = %s
                        AND u.leaved = FALSE
                        AND ubl.id IS NULL
                    ORDER BY up.updated_at DESC
                    LIMIT 20 OFFSET %s
                    """,
                    (user_id, offset),
                )
                rows = await cur.fetchall()
                return [
                    {
                        "pockerId": row[0],
                        "pokedAt": row[1].strftime("%Y-%m-%d %H:%M:%S"),
                        "pokeCount": row[2],
                    }
                    for row in rows
                ]

    async def favorite_user(self, user_id: str, target_user_id: str) -> bool:
        """
        유저 즐겨찾기 하기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 1
                    FROM users_favorite_list
                    WHERE user_id = %s AND favorite_user_id = %s
                    """,
                    (user_id, target_user_id),
                )
                is_favorited = await cur.fetchone()

                if is_favorited:
                    await cur.execute(
                        """
                        DELETE FROM users_favorite_list
                        WHERE user_id = %s AND favorite_user_id = %s
                        """,
                        (user_id, target_user_id),
                    )
                    await cur.execute(
                        """
                        INSERT INTO users_favorite_list_log (user_id, favorite_user_id, favorite_type)
                        VALUES (%s, %s, 'UNFAVORITE')
                        """,
                        (user_id, target_user_id),
                    )
                    await conn.commit()
                    return False

                await cur.execute(
                    """
                    INSERT INTO users_favorite_list (user_id, favorite_user_id, created_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    """,
                    (user_id, target_user_id),
                )
                await cur.execute(
                    """
                    INSERT INTO users_favorite_list_log (user_id, favorite_user_id, favorite_type)
                    VALUES (%s, %s, 'FAVORITE')
                    """,
                    (user_id, target_user_id),
                )
                await conn.commit()
                return True

    async def fetch_user_unlock_count(self, user_id: str) -> dict:
        """
        유저가 해금한 목록 수 가져오기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 
                        (
                            SELECT COUNT(DISTINCT ucpv.viewed_id) 
                            FROM user_credit_profile_view ucpv
                            WHERE ucpv.user_id = %s
                            AND NOT EXISTS (
                                SELECT 1
                                FROM user_block_list ubl
                                WHERE ubl.block_user_id = %s
                                  AND ubl.blocked_user_id = ucpv.viewed_id
                            )
                            AND NOT EXISTS (
                                SELECT 1
                                FROM user_block_list ubl2
                                WHERE ubl2.block_user_id = ucpv.viewed_id
                                    AND ubl2.blocked_user_id = %s
                            )
                        ) AS profileCount,
                        (
                            SELECT COUNT(DISTINCT ucsv.viewed_id) 
                            FROM user_credit_secret_view ucsv
                            WHERE ucsv.user_id = %s
                            AND ucsv.created_at >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 24 HOUR)
                            AND NOT EXISTS (
                                SELECT 1
                                FROM user_block_list ubl
                                WHERE ubl.block_user_id = %s
                                  AND ubl.blocked_user_id = ucsv.viewed_id
                            )
                            AND NOT EXISTS (
                                SELECT 1
                                FROM user_block_list ubl2
                                WHERE ubl2.block_user_id = ucsv.viewed_id
                                    AND ubl2.blocked_user_id = %s
                            )
                        ) AS secretCount
                    """,
                    (user_id, user_id, user_id, user_id, user_id, user_id),
                )
                rows = await cur.fetchone()
                columns = [col[0] for col in cur.description]
                return CountRow(**dict(zip(columns, rows)))

    async def fetch_user_id(self, user_no: int) -> Optional[str]:
        """
        유저의 user_id를 가져오기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE user_no = %s
                        AND leaved = FALSE
                    LIMIT 1
                    """,
                    (user_no,),
                )
                result = await cur.fetchone()
                if not result:
                    return None
                return result[0]

    async def fetch_user_alarm_setting(self, user_id: str) -> dict:
        """
        유저의 알림 설정 상태 가져오기
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT profile_alarm_agree, feed_like_alarm_agree, feed_comment_alarm_agree,
                            post_like_alarm_agree, post_comment_alarm_agree, secret_alarm_agree,
                            personal_chat_alarm_agree, group_chat_alarm_agree
                    FROM users
                    WHERE id = %s
                    """,
                    (user_id,),
                )
                result = await cur.fetchone()
                if not result:
                    return False
                keys = [
                    "profile",
                    "feed_like",
                    "feed_comment",
                    "post_like",
                    "post_comment",
                    "secret",
                    "personal_chat",
                    "group_chat",
                ]
                return dict(zip(keys, result))

    async def fetch_user_credit_history(
        self,
        page: int,
        type: str,
        user_id: str,
    ):
        offset = (page - 1) * 20
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                if type == "all":
                    await cur.execute(
                        """
                        SELECT amount, description, created_at
                        FROM credit_history
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                        LIMIT 20 OFFSET %s
                        """,
                        (user_id, offset),
                    )
                    credit_history = await cur.fetchall()
                    return credit_history
                elif type == "use":
                    await cur.execute(
                        """
                        SELECT amount, description, created_at
                        FROM credit_history
                        WHERE user_id = %s AND amount < 0
                        ORDER BY created_at DESC
                        LIMIT 20 OFFSET %s
                        """,
                        (user_id, offset),
                    )
                    credit_history = await cur.fetchall()
                    return credit_history
                elif type == "earn":
                    await cur.execute(
                        """
                        SELECT amount, description, created_at
                        FROM credit_history
                        WHERE user_id = %s AND amount > 0
                        ORDER BY created_at DESC
                        LIMIT 20 OFFSET %s
                        """,
                        (user_id, offset),
                    )
                    credit_history = await cur.fetchall()
                    return credit_history

    async def follow_user(
        self,
        follower_id: str,
        follow_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 1
                    FROM users_follow_list
                    WHERE follower_user_id = %s AND following_user_id = %s 
                    """,
                    (follower_id, follow_id),
                )
                is_followed = await cur.fetchone()
                # 팔로우 취소
                if is_followed:
                    await cur.execute(
                        """
                        DELETE FROM users_follow_list
                        WHERE follower_user_id = %s AND following_user_id = %s
                        """,
                        (
                            follower_id,
                            follow_id,
                        ),
                    )
                    await conn.commit()
                    return False
                # 팔로우
                await cur.execute(
                    """
                    INSERT INTO users_follow_list (follower_user_id, following_user_id, created_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    """,
                    (follower_id, follow_id),
                )
                await conn.commit()
                return True

    async def fetch_follow_list(
        self,
        user_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT following_user_id
                    FROM users_follow_list
                    WHERE follower_user_id = %s
                    """,
                    (user_id,),
                )
                rows = await cur.fetchall()
                return [row[0] for row in rows]

    async def fetch_follower_list(
        self,
        user_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT follower_user_id
                    FROM users_follow_list
                    WHERE following_user_id = %s
                    """,
                    (user_id,),
                )
                rows = await cur.fetchall()
                return [row[0] for row in rows]

    async def insert_refferal_code(
        self,
        user_id: str,
        referral_code: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 1
                    FROM users_refferal_code
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )
                is_exist = await cur.fetchone()
                if is_exist:
                    return False

                await cur.execute(
                    """
                    INSERT INTO users_refferal_code (user_id, referral_code, created_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    """,
                    (
                        user_id,
                        referral_code,
                    ),
                )
                await conn.commit()
                return True

    async def create_biz_review(
        self,
        user_id: str,
        biz_id: str,
        content: str,
        rating: int,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO biz_review (user_id, biz_id, content, rating)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        biz_id,
                        content,
                        rating,
                    ),
                )

                review_id = cur.lastrowid
                await conn.commit()
                return review_id

    async def insert_biz_review_images(
        self,
        review_id: int,
        user_id: str,
        image_urls: list[str],
        start_index=0,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                for index, url in enumerate(image_urls):
                    await cur.execute(
                        """
                        INSERT INTO biz_review_image (review_id, user_id, url, `index`, created_at)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        """,
                        (
                            review_id,
                            user_id,
                            url,
                            start_index + index,
                        ),
                    )
                await conn.commit()
                return True

    async def delete_biz_review(
        self,
        user_id: str,
        review_id: int,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE biz_review
                    SET deleted = TRUE
                    WHERE id = %s AND user_id = %s
                    """,
                    (
                        review_id,
                        user_id,
                    ),
                )
                if cur.rowcount == 0:
                    return False
                await conn.commit()
                return True

    async def is_owner(self, user_id: str, review_id: int) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM biz_review
                    WHERE id = %s AND user_id = %s
                    """,
                    (review_id, user_id),
                )
                result = await cur.fetchone()
                return result[0] > 0

    async def get_review_images(self, review_id: int) -> List[str]:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT url
                    FROM biz_review_image
                    WHERE review_id = %s AND use_yn = TRUE
                    ORDER BY `index`
                    """,
                    (review_id,),
                )
                rows = await cur.fetchall()
                return [url for (url,) in rows]

    async def update_review_images(
        self,
        review_id: int,
        user_id: str,
        keep_images: List[str],
        remove_images: List[str],
        uploaded_urls: List[str],
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await conn.begin()

                # 삭제할 이미지 use_yn = FALSE
                if remove_images:
                    for url in remove_images:
                        await cur.execute(
                            """
                            UPDATE biz_review_image
                            SET use_yn = FALSE, updated_at = NOW()
                            WHERE review_id = %s AND url = %s
                            """,
                            (review_id, url),
                        )

                # 유지할 이미지 index 재정렬
                for idx, url in enumerate(keep_images):
                    await cur.execute(
                        """
                        UPDATE biz_review_image
                        SET `index` = %s, updated_at = NOW()
                        WHERE review_id = %s AND url = %s AND use_yn = TRUE
                        """,
                        (idx, review_id, url),
                    )

                # 새 이미지 삽입
                start_index = len(keep_images)
                for idx, url in enumerate(uploaded_urls, start=start_index):
                    await cur.execute(
                        """
                        INSERT INTO biz_review_image (review_id, user_id, `index`, url)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (review_id, user_id, idx, url),
                    )

                await conn.commit()

    async def update_biz_review(
        self,
        review_id: int,
        content: str,
        rating: int,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE biz_review
                    SET content = %s, rating = %s
                    WHERE id = %s
                    """,
                    (content, rating, review_id),
                )

    async def get_review(self, review_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT review_id, user_id, biz_id, content, rating, created_at, updated_at
                    FROM biz_review
                    WHERE id = %s AND deleted = FALSE
                    """,
                    (review_id,),
                )
                return await cur.fetchone()

    async def block_biz_review(
        self,
        user_id: str,
        review_id: int,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO biz_review_block_list (block_user_id, review_id, created_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    """,
                    (
                        user_id,
                        review_id,
                    ),
                )
                await conn.commit()
                return True

    async def report_biz_review(
        self,
        user_id: str,
        review_id: int,
        reason: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO biz_review_report_list (review_id, report_user_id, reason, status, created_at)
                    VALUES (%s, %s, %s, 'PENDING', CURRENT_TIMESTAMP)
                    """,
                    (
                        review_id,
                        user_id,
                        reason,
                    ),
                )
                await conn.commit()
                return True

    async def fetch_biz_review_list(self, user_id: str, biz_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 
                        br.id,
                        br.user_id,
                        u.nickname,
                        br.biz_id,
                        br.content,
                        br.rating,
                        br.created_at,
                        bra.answer_content,
                        bra.answer_created_at
                    FROM biz_review br
                    JOIN users u 
                        ON br.user_id = u.id
                    LEFT JOIN (
                        SELECT review_id, content AS answer_content, created_at AS answer_created_at
                        FROM biz_review_answer_list
                    ) bra
                        ON bra.review_id = br.id
                    WHERE br.biz_id = %s
                    AND br.deleted = FALSE
                    AND br.user_id NOT IN (
                        SELECT blocked_user_id
                        FROM user_block_list
                        WHERE block_user_id = %s
                    )
                    AND br.user_id NOT IN (
                        SELECT block_user_id
                        FROM user_block_list
                        WHERE blocked_user_id = %s
                    )
                    AND br.id NOT IN (
                        SELECT review_id
                        FROM biz_review_block_list
                        WHERE block_user_id = %s
                    )
                    ORDER BY br.id DESC
                    """,
                    (biz_id, user_id, user_id, user_id),
                )

                rows = await cur.fetchall()
                if not rows:
                    return []

                columns = [col[0] for col in cur.description]
                return [BizReviewRow(**dict(zip(columns, row))) for row in rows]

    async def fetch_biz_list(
        self,
        user_id: str,
        page: int,
    ):
        offset = (page - 1) * 20
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT b.id, 
                           b.biz_id, 
                           b.store_type, 
                           b.store_name,
                           b.email,
                           b.tags,
                           b.address,
                           b.business_hours,
                           b.phone, 
                           b.manager_phone, 
                           b.latitude,
                           b.longitude
                    FROM biz_account b
                    ORDER BY b.created_at DESC
                    LIMIT 20 OFFSET %s
                    """,
                    (offset,),
                )
                rows = await cur.fetchall()
                return rows

    async def fetch_biz_detail(
        self,
        user_id: str,
        biz_pk: int,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:

                await cur.execute(
                    """
                    SELECT 
                        b.id,
                        b.biz_id,
                        b.store_type,
                        b.store_name,
                        b.email,
                        b.tags,
                        b.address,
                        b.business_hours,
                        b.phone,
                        b.manager_phone,
                        b.latitude,
                        b.longitude,

                        CASE 
                            WHEN f.user_id IS NOT NULL THEN TRUE
                            ELSE FALSE
                        END AS is_follow

                    FROM biz_account b
                    LEFT JOIN biz_follow_list f
                        ON f.biz_id = b.biz_id
                        AND f.user_id = %s 

                    WHERE b.id = %s
                    LIMIT 1
                    """,
                    (user_id, biz_pk),
                )

                row = await cur.fetchone()
                if not row:
                    return None

                columns = [col[0] for col in cur.description]
                return dict(zip(columns, row))

    async def use_biz_coupon(
        self,
        user_id: str,
        coupon_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:

                # 쿠폰 정보 조회
                await cur.execute(
                    """
                    SELECT start_date, expired_date, amount, use_amount
                    FROM biz_coupon
                    WHERE id = %s AND deleted = FALSE
                    FOR UPDATE
                    """,
                    (coupon_id,),
                )

                row = await cur.fetchone()
                if not row:
                    return "none"

                await cur.execute(
                    """
                    SELECT 1
                    FROM biz_coupon_history
                    WHERE coupon_id = %s AND user_id = %s
                    LIMIT 1
                    """,
                    (coupon_id, user_id),
                )
                used_before = await cur.fetchone()
                if used_before:
                    return "used"

                start_date, expired_date, amount, use_amount = row
                start_date = to_datetime(start_date)
                expired_date = to_datetime(expired_date)
                now = datetime.utcnow()

                # 유효기간 체크하기
                if expired_date is not None:
                    if start_date is not None:
                        if not (start_date <= now <= expired_date):
                            return "expired"
                    else:
                        if now > expired_date:
                            return "expired"

                # 수량 체크하기
                if amount is not None:
                    # 수량 소진
                    if amount - use_amount <= 0:
                        return "amount"

                    # 수량 1 감소
                    await cur.execute(
                        """
                        UPDATE biz_coupon
                        SET use_amount = use_amount + 1
                        WHERE id = %s
                        """,
                        (coupon_id,),
                    )

                # 쿠폰 사용기록 저장
                await cur.execute(
                    """
                    INSERT INTO biz_coupon_history (coupon_id, user_id, used_at)
                    VALUES (%s, %s, NOW())
                    """,
                    (coupon_id, user_id),
                )

                await conn.commit()
                return True

    async def check_biz_account(
        self,
        user_id: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 1
                    FROM biz_account
                    WHERE biz_id = %s AND leaved = FALSE
                    LIMIT 1
                    """,
                    (user_id,),
                )
                row = await cur.fetchone()
                return bool(row)
