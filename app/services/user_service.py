from app.db.user import User
from app.db.db_connection import db
from sqlalchemy import text
from typing import List

class UserService:
    def __init__(self):
        self.db = db

    async def create_user(self, user: User) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM users WHERE id = %s", (user.id,))
                result = await cur.fetchone()
                if result:
                    return False

                try:
                    await conn.begin()

                    insert_sql = """
                        INSERT INTO users (
                            id, fcm, sns, name, phone, provider, email, nickname, relation, position,
                            country, age, height, weight, hashtags,
                            marketing_agree, service_agree, personal_agree,
                            personal_chat_alarm_agree, group_chat_alarm_agree,
                            post_comment_alarm_agree, post_like_alarm_agree, night_agree, leaved
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s,
                            %s, %s, %s, %s
                        )
                    """

                    await cur.execute( insert_sql, (
                        user.id, user.fcm, user.sns, user.name, user.phone, user.provider, user.email,
                        user.nickname, user.relation, user.position,
                        user.country, user.age, user.height, user.weight, 
                        user.hashtags.json(),
                        user.marketingAgree, user.serviceAgree, user.personalAgree,
                        user.personalChatAlarm, user.groupChatAlarm,
                        user.postCommentAlarm, user.postLikeAlarm, user.nightAgree, user.leave
                    ))

                    await conn.commit()
                    return True
                except Exception as e:
                    await conn.rollback()
                    print(f"Error creating user: {e}")
                    return False


    async def check_nickname(self, nickname: str) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM users WHERE nickname = %s", (nickname,))
                result = await cur.fetchone()
                return result is not None
