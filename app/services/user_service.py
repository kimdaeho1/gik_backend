from fastapi import UploadFile
from datetime import datetime
from app.utils.s3_upload import upload_file_to_s3
from app.db.user import User, Hashtags
from app.db.db_connection import db
from sqlalchemy import text
from typing import List


class UserService:
    def __init__(self):
        self.db = db

    async def create_user(
        self,
        id: str,
        fcm: str,
        email: str,
        name: str,
        phone: str,
        birthday: str,
        provider: str,
        sns: str,
        nickname: str,
        profile_images: List[UploadFile],
        age: int,
        height: int,
        weight: int,
        country: str,
        position: str,
        relation: str,
        hashtags: Hashtags,
        personal_chat_alarm: bool,
        group_chat_alarm: bool,
        post_comment_alarm: bool,
        post_like_alarm: bool,
        service_agree: bool,
        personal_agree: bool,
        marketing_agree: bool,
        night_agree: bool,
        leave: bool
    ) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM users WHERE id = %s", (id,))
                result = await cur.fetchone()
                if result:
                    return False

                try:
                    await conn.begin()

                    insert_sql = """
                        INSERT INTO users (
                            id, fcm, sns, name, phone, provider, email, nickname,
                            birthday, age, height, weight, country, position, relation,
                            hashtags, marketing_agree, service_agree, personal_agree,
                            personal_chat_alarm_agree, group_chat_alarm_agree,
                            post_comment_alarm_agree, post_like_alarm_agree,
                            night_agree, leaved
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s,
                            %s, %s,
                            %s, %s
                        )
                    """
                    await cur.execute(insert_sql, (
                        id, fcm, sns, name, phone, provider, email, nickname,
                        birthday, age, height, weight, country, position, relation,
                        hashtags.json(), marketing_agree, service_agree, personal_agree,
                        personal_chat_alarm, group_chat_alarm,
                        post_comment_alarm, post_like_alarm,
                        night_agree, leave
                    ))

                    for idx, file in enumerate(profile_images):
                        now = datetime.now().strftime("%Y%m%d_%H%M%S%f")[:-3]
                        extension = file.filename.split(".")[-1] or "jpg"
                        filename = f"{now}.{extension}"
                        s3_key = f"user_profile/{id}/"

                        file.file.seek(0)
                        if not upload_file_to_s3(file.file, s3_key, filename):
                            raise Exception(f"S3 업로드 실패: {file.filename}")

                        base_url = "https://gik-profile.couplematch.co.kr/"
                        image_url = f"{base_url}{s3_key}{filename}"

                        await cur.execute(
                            """
                            INSERT INTO user_images (user_id, `index`, url, use_yn)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (id, idx, image_url, True)
                        )

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
