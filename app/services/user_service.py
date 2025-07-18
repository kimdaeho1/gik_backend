from fastapi import UploadFile , HTTPException
from datetime import datetime
from app.utils.s3_upload import upload_file_to_s3
from app.db.user import User, Hashtags, UserProfileResponse
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
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1 FROM users WHERE nickname = %s", (nickname,))
                    result = await cur.fetchone()
                    return result is not None
        except Exception as e:
            print(f"닉네임 중복확인실패: {e}")
            raise HTTPException(
                status_code=500,
                detail="닉네임 중복 확인 실패"
            )


    async def fetch_my_profile(self, id: str) -> UserProfileResponse | None:
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    user_query = """
                    SELECT
                        id, nickname, age, height, weight, sns, 
                        relation, position, country, hashtags,
                        provider, marketing_agree, night_agree,
                        personal_chat_alarm_agree, group_chat_alarm_agree,
                        post_comment_alarm_agree, post_like_alarm_agree,
                        banned, unbanned_dt
                    FROM users
                    WHERE id = %s
                    """

                    await cur.execute(user_query, (id,))
                    user_row = await cur.fetchone()
                    if not user_row:
                        raise HTTPException(
                            status_code=404,
                            detail="내 정보 조회 실패"
                        )

                    (
                        id, nickname, age, height, weight, sns,
                        relation, position, country, hashtags_json,
                        provider, marketing_agree, night_agree,
                        personal_chat_alarm, group_chat_alarm,
                        post_comment_alarm, post_like_alarm,
                        banned, unbanned_dt
                    ) = user_row
                    
                    hashtags = Hashtags.parse_raw(hashtags_json)

                    profile_images_query = """
                    SELECT url 
                    FROM user_images 
                    WHERE user_id = %s AND use_yn = TRUE
                    """

                    await cur.execute(profile_images_query, (id,))
                    profile_images = [row[0] for row in await cur.fetchall()]

                    block_user_query = """
                        SELECT blocked_user_id FROM user_block_list WHERE block_user_id = %s
                    """
                    await cur.execute(block_user_query, (id,))
                    block_user_list = [row[0] for row in await cur.fetchall()]

                    block_post_query = """
                        SELECT blocked_post_id FROM post_block_list WHERE block_user_id = %s
                    """
                    await cur.execute(block_post_query, (id,))
                    block_post_list = [row[0] for row in await cur.fetchall()]

                    block_comment_query = """
                        SELECT blocked_comment_id FROM comment_block_list WHERE block_user_id = %s
                    """
                    await cur.execute(block_comment_query, (id,))
                    block_comment_list = [row[0] for row in await cur.fetchall()]

                    return UserProfileResponse(
                        id=id,
                        nickname=nickname,
                        age=age,
                        height=height,
                        weight=weight,
                        sns=sns,
                        relation=relation,
                        provider=provider,
                        position=position,
                        country=country,
                        hashtags=hashtags,
                        profileImages=profile_images,
                        marketingAlarm=marketing_agree,
                        nightAlarm=night_agree,
                        personalChatAlarm=personal_chat_alarm,
                        groupChatAlarm=group_chat_alarm,
                        postCommentAlarm=post_comment_alarm,
                        postLikeAlarm=post_like_alarm,
                        banned=banned,
                        unBannedDate=unbanned_dt,
                        blockUserList=block_user_list,
                        blockPostList=block_post_list,
                        blockCommentList=block_comment_list,
                    )
        except Exception as e:
            print(f"Error fetching user profile: {e}")
            raise HTTPException(
                status_code=500,
                detail="내 정보 없음"
            )


    async def update_user_nickname(self, id: str, nickname: str) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM users WHERE id = %s",(id, ))
                result = await cur.fetchone()
                if not result:
                    return "not_found"
                
                await cur.execute("SELECT 1 FROM users WHERE nickname = %s", (nickname, ))
                nickname_exist = await cur.fetchone()
                if nickname_exist:
                    return "duplicate"
                
                await cur.execute(
                    "UPDATE users SET nickname = %s WHERE id = %s",
                    (nickname, id)
                )
                await conn.commit()
                return "success"


    async def update_user_hashtag(self, id: str, hashtags: Hashtags) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM users WHERE id = %s", (id, ))
                result = await cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="User not found"
                    )
                
                await cur.execute(
                    "UPDATE users SET hashtags = %s WHERE id = %s",
                    (hashtags.json(), id)
                )
                await conn.commit()
                return True
    
    
    async def update_user_info(
        self,
        id: str,
        age: int,
        height: int,
        weight: int,
        country: str
    ) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM users WHERE id = %s", (id, ))
                result = await cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="User not found"
                    )
                
                await cur.execute(
                    """
                    UPDATE users 
                    SET age = %s, height = %s, weight = %s, country = %s 
                    WHERE id = %s
                    """,
                    (age, height, weight, country, id)
                )
                await conn.commit()
                return True


    async def update_user_fcm(self, id: str, fcm: str) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM users WHERE id = %s", (id, ))
                result = await cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="User not found"
                    )
                
                await cur.execute(
                    "UPDATE users SET fcm = %s WHERE id = %s",
                    (fcm, id)
                )
                await conn.commit()
                return True

    
    async def update_user_relation(self, id: str, relation: str) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM users WHERE id = %s", (id, ))
                result = await cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="User not found"
                    )
                
                await cur.execute(
                    "UPDATE users SET relation = %s WHERE id = %s",
                    (relation, id)
                )
                await conn.commit()
                return True
    

    async def update_user_position(self, id: str, position: str) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM users WHERE id = %s", (id, ))
                result = await cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="User not found"
                    )
                
                await cur.execute(
                    "UPDATE users SET position = %s WHERE id = %s",
                    (position, id)
                )
                await conn.commit()
                return True
    

    async def update_user_alarm(
        self,
        id: str,
        type: str,
        value: bool,
    ) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM users WHERE id = %s", (id,))
                result = await cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="User not found"
                    )
                
                column_map = {
                    "personal_chat": "personal_chat_alarm_agree",
                    "group_chat": "group_chat_alarm_agree",
                    "post_comment": "post_comment_alarm_agree",
                    "post_like": "post_like_alarm_agree",
                    "night_agree": "night_agree",
                }

                if type not in column_map:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid alarm type"
                    )
                column_name = column_map[type]
                await cur.execute(
                    f"UPDATE users SET {column_name} = %s WHERE id = %s",
                    (value, id)
                )
                await conn.commit()
                return True


    async def fetch_user_profile(self, user_id: str) -> UserDetailResponse | None:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                user_query = """
                SELECT
                        id, nickname, relation, position,
                        country, age, height, weight, hashtags
                FROM users
                WHERE id = %s
                """

                await cur.execute(user_query, (user_id,))
                user_row = await cur.fetchone()

                if not user_row:
                    return None
                
                user_dict = dict(zip([col[0] for col in cur.description], user_row))
                
                hashtags = Hashtags.parse_raw(user_dict['hashtags'])
                user_dict['hashtags'] = hashtags

                # 프로필 이미지 조회
                image_query = """
                    SELECT
                        `index`, url
                    FROM user_images
                    WHERE 
                        user_id = %s and use_yn = TRUE
                    ORDER BY `index`
                """

                await cur.execute(image_query, (user_id,))
                images = await cur.fetchall()

                profile_images = []
                for index, row in enumerate(images):
                    profile_images.append(row[1])

                user_dict['profileImages'] = profile_images

                return UserDetailResponse(**user_dict)

    
    async def block_user(self, id: str, user_id: str) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM users WHERE id = %s", (id,))
                result = await cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="User not found"
                    )
                
                await cur.execute(
                    "INSERT INTO user_block_list (block_user_id, blocked_user_id) VALUES (%s, %s)",
                    (id, user_id)
                )
                await conn.commit()
                return True
 
    
    async def report_user(
        self,
        chatId: str,
        reportUserId: str,
        reportedUserId: str,
        reason: str
    ) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM users WHERE id = %s", (reportUserId,))
                result = await cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="Reporting user not found"
                    )
                
                await cur.execute("SELECT 1 FROM users WHERE id = %s", (reportedUserId,))
                result = await cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="Reported user not found"
                    )
                
                await cur.execute(
                    """
                    INSERT INTO user_reports (chat_id, report_user_id, reported_user_id, reason)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (chatId, reportUserId, reportedUserId, reason)
                )
                await conn.commit()
                return True
            
    
    async def fetch_user_list(
        self,
        user_id: List[str]
    ) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                if not user_id:
                    return []

                placeholders = ', '.join(['%s'] * len(user_id))
                query = f"""
                    SELECT id, nickname, age, height, weight, relation, position, hashtags
                    FROM users
                    WHERE id IN ({placeholders})
                """
                
                await cur.execute(query, tuple(user_id))
                rows = await cur.fetchall()

                user_profiles = []
                for row in rows:
                    user_dict = dict(zip([col[0] for col in cur.description], row))
                    user_dict['hashtags'] = Hashtags.parse_raw(user_dict['hashtags'])
                    user_profiles.append(user_dict)

                return user_profiles

    
    async def fetch_user_id_list(
        self,    
    ) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                query = """
                    SELECT id
                    FROM users
                    WHERE leaved = FALSE
                """
                
                await cur.execute(query)
                rows = await cur.fetchall()

                user_id_list = [row[0] for row in rows]

                return user_id_list
    

    async def fetch_user_fcm_list(
        self,
        user_id: List[str]
    ) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                if not user_id:
                    return []

                placeholders = ', '.join(['%s'] * len(user_id))
                query = f"""
                    SELECT id, fcm
                    FROM users
                    WHERE id IN ({placeholders})
                """
                
                await cur.execute(query, tuple(user_id))
                rows = await cur.fetchall()

                user_fcm_list = [row[1] for row in rows if row[1]]

                return user_fcm_list


    async def leave_user(
        self,
        id: str,
        reason: str
    ) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM users WHERE id = %s", (id,))
                result = await cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="User not found"
                    )
                
                await cur.execute(
                    "UPDATE users SET leaved = TRUE WHERE id = %s",
                    (id,)
                )
                
                await cur.execute(
                    "INSERT INTO leaved_users (user_id, reason) VALUES (%s, %s)",
                    (id, reason)
                )
                await conn.commit()
                return True
