from fastapi import UploadFile , HTTPException
from datetime import datetime
from app.utils.s3_upload import upload_file_to_s3, CLOUDFRONT_URL
from app.db.user import User, Hashtags, UserProfileResponse, UserDetailResponse
from app.db.db_connection import db
from sqlalchemy import text
from typing import List, Optional


class UserService:
    def __init__(self):
        self.db = db
    
    async def fetch_active_user(
        self,
        user_id: str
    ) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 1
                    FROM users
                    WHERE id = %s AND leaved = FALSE
                    """
                    , (user_id, )
                )
                
                result = await cur.fetchone()
                if result:
                    return True
                else:
                    return False
    
    # TODO : self_introduction 필드 추가.
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
        self_introduction: Optional[str],
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
                            hashtags, self_introduction, marketing_agree, service_agree, personal_agree,
                            personal_chat_alarm_agree, group_chat_alarm_agree,
                            post_comment_alarm_agree, post_like_alarm_agree,
                            night_agree, leaved
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s,
                            %s, %s,
                            %s, %s
                        )
                    """
                    await cur.execute(insert_sql, (
                        id, fcm, sns, name, phone, provider, email, nickname,
                        birthday, age, height, weight, country, position, relation,
                        hashtags.json(), self_introduction, marketing_agree, service_agree, personal_agree,
                        personal_chat_alarm, group_chat_alarm,
                        post_comment_alarm, post_like_alarm,
                        night_agree, leave
                    ))
                    
                    user_no = cur.lastrowid
                    image_urls = []

                    for idx, file in enumerate(profile_images):
                        now = datetime.now().strftime("%Y%m%d_%H%M%S%f")[:-3]
                        extension = file.filename.split(".")[-1] or "jpg"
                        filename = f"{now}.{extension}"
                        s3_key = f"user_profile/{id}/"

                        file.file.seek(0)
                        if not upload_file_to_s3(file.file, s3_key, filename):
                            raise Exception(f"S3 업로드 실패: {file.filename}")

                        image_url = f"{CLOUDFRONT_URL}/{s3_key}{filename}"
                        image_urls.append(image_url)
                        await cur.execute(
                            """
                            INSERT INTO user_images (user_id, `index`, url, use_yn)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (id, idx, image_url, True)
                        )
                    
                    image_urls = ','.join(image_urls)
                    insert_history = """
                        INSERT INTO users_history (
                            user_no, id, fcm, sns, name, phone, provider, email, nickname,
                            birthday, age, height, weight, country, position, relation,
                            hashtags, self_introduction, marketing_agree, service_agree, personal_agree,
                            personal_chat_alarm_agree, group_chat_alarm_agree,
                            post_comment_alarm_agree, post_like_alarm_agree,
                            night_agree, leaved, image_list
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s,
                            %s, %s,
                            %s, %s, %s
                        )
                    """
                    await cur.execute(insert_history, (
                        user_no, id, fcm, sns, name, phone, provider, email, nickname,
                        birthday, age, height, weight, country, position, relation,
                        hashtags.json(), self_introduction, marketing_agree, service_agree, personal_agree,
                        personal_chat_alarm, group_chat_alarm,
                        post_comment_alarm, post_like_alarm,
                        night_agree, leave, image_urls
                    ))

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


    async def fetch_my_profile(self, user_id: str) -> UserProfileResponse | None:
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    user_query = """
                    SELECT
                        id, nickname, birthday, age, height, weight, sns, 
                        relation, position, country, hashtags, self_introduction, talk_style,
                        provider, marketing_agree, night_agree,
                        personal_chat_alarm_agree, group_chat_alarm_agree,
                        post_comment_alarm_agree, post_like_alarm_agree,
                        banned, unbanned_dt, last_connected_at,
                        latitude, longitude
                    FROM users
                    WHERE id = %s AND leaved = FALSE
                    """

                    await cur.execute(user_query, (user_id,))
                    user_row = await cur.fetchone()
                    if not user_row:
                        return {}

                    (
                        id, nickname, birthday, age, height, weight, sns,
                        relation, position, country, hashtags_json, self_introduction, talk_style,
                        provider, marketing_agree, night_agree,
                        personal_chat_alarm, group_chat_alarm,
                        post_comment_alarm, post_like_alarm,
                        banned, unbanned_dt, last_connected_at,
                        latitude, longitude
                    ) = user_row
                    
                    hashtags = Hashtags.parse_raw(hashtags_json)

                    profile_images_query = """
                    SELECT url 
                    FROM user_images 
                    WHERE user_id = %s AND use_yn = TRUE
                    """

                    await cur.execute(profile_images_query, (user_id,))
                    profile_images = [row[0] for row in await cur.fetchall()]

                    block_user_query = """
                        SELECT blocked_user_id FROM user_block_list WHERE block_user_id = %s
                    """
                    await cur.execute(block_user_query, (user_id,))
                    block_user_list = [row[0] for row in await cur.fetchall()]

                    block_post_query = """
                        SELECT blocked_post_id FROM post_block_list WHERE block_user_id = %s
                    """
                    await cur.execute(block_post_query, (user_id,))
                    block_post_list = [row[0] for row in await cur.fetchall()]

                    block_comment_query = """
                        SELECT blocked_comment_id FROM comment_block_list WHERE block_user_id = %s
                    """
                    await cur.execute(block_comment_query, (user_id,))
                    block_comment_list = [row[0] for row in await cur.fetchall()]

                    return UserProfileResponse(
                        id=user_id,
                        nickname=nickname,
                        birthday=birthday,
                        age=age,
                        height=height,
                        weight=weight,
                        sns=sns,
                        relation=relation,
                        provider=provider,
                        position=position,
                        country=country,
                        hashtags=hashtags,
                        selfIntroduction=self_introduction,
                        talkStyle=talk_style,
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
                        lastConnectedAt=last_connected_at,
                        latitude=latitude,
                        longitude=longitude
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
                await cur.execute("SELECT 1 FROM users WHERE id = %s AND leaved = FALSE",(id, ))
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
                
                # updated_at 필드 업데이트
                await cur.execute(
                    "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (id, )
                )
                
                await cur.execute("SELECT * FROM users WHERE id = %s", (id, ))
                user_row = await cur.fetchone()
                columns = [col[0] for col in cur.description]
                
                if user_row:
                    placeholders = ', '.join(['%s'] * len(columns))
                    columns_sql = ', '.join(columns)
                    insert_history = f"""
                    INSERT INTO users_history ({columns_sql})
                    VALUES ({placeholders})
                    """
                    await cur.execute(insert_history, user_row)
                
                await conn.commit()
                return "success"


    async def update_user_hashtag(self, id: str, hashtags: Hashtags) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM users WHERE id = %s AND leaved = FALSE", (id, ))
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
                
                # updated_at 필드 업데이트
                await cur.execute(
                    "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (id, )
                )
                
                await cur.execute("SELECT * FROM users WHERE id = %s", (id, ))
                user_row = await cur.fetchone()
                columns = [col[0] for col in cur.description]
                
                if user_row:
                    placeholders = ', '.join(['%s'] * len(columns))
                    columns_sql = ', '.join(columns)
                    insert_history = f"""
                    INSERT INTO users_history ({columns_sql})
                    VALUES ({placeholders})
                    """
                    await cur.execute(insert_history, user_row)
                
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
                await cur.execute("SELECT 1 FROM users WHERE id = %s AND leaved = FALSE", (id, ))
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
                
                #updated_at 필드 업데이트
                await cur.execute(
                    "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (id, )
                )
                
                await cur.execute("SELECT * FROM users WHERE id = %s", (id, ))
                user_row = await cur.fetchone()
                columns = [col[0] for col in cur.description]
                
                if user_row:
                    placeholders = ', '.join(['%s'] * len(columns))
                    columns_sql = ', '.join(columns)
                    insert_history = f"""
                    INSERT INTO users_history ({columns_sql})
                    VALUES ({placeholders})
                    """
                    await cur.execute(insert_history, user_row)
                
                await conn.commit()
                return True


    async def update_user_fcm(self, id: str, fcm: str) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM users WHERE id = %s AND leaved = FALSE", (id, ))
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
                
                # updated_at 필드 업데이트
                await cur.execute(
                    "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (id, )
                )
                
                await cur.execute("SELECT * FROM users WHERE id = %s", (id, ))
                user_row = await cur.fetchone()
                columns = [col[0] for col in cur.description]
                
                if user_row:
                    placeholders = ', '.join(['%s'] * len(columns))
                    columns_sql = ', '.join(columns)
                    insert_history = f"""
                    INSERT INTO users_history ({columns_sql})
                    VALUES ({placeholders})
                    """
                    await cur.execute(insert_history, user_row)
                
                await conn.commit()
                return True

    
    async def update_user_relation(self, id: str, relation: str) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM users WHERE id = %s AND leaved = FALSE", (id, ))
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
                
                # updated_at 필드 업데이트
                await cur.execute(
                    "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (id, )
                )
                
                await cur.execute("SELECT * FROM users WHERE id = %s", (id, ))
                user_row = await cur.fetchone()
                columns = [col[0] for col in cur.description]
                
                if user_row:
                    placeholders = ', '.join(['%s'] * len(columns))
                    columns_sql = ', '.join(columns)
                    insert_history = f"""
                    INSERT INTO users_history ({columns_sql})
                    VALUES ({placeholders})
                    """
                    await cur.execute(insert_history, user_row)
                
                await conn.commit()
                return True
    

    async def update_user_position(self, id: str, position: str) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM users WHERE id = %s AND leaved = FALSE", (id, ))
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
                
                # updated_at 필드 업데이트
                await cur.execute(
                    "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (id, )
                )
                
                await cur.execute("SELECT * FROM users WHERE id = %s", (id, ))
                user_row = await cur.fetchone()
                columns = [col[0] for col in cur.description]
                
                if user_row:
                    placeholders = ', '.join(['%s'] * len(columns))
                    columns_sql = ', '.join(columns)
                    insert_history = f"""
                    INSERT INTO users_history ({columns_sql})
                    VALUES ({placeholders})
                    """
                    await cur.execute(insert_history, user_row)
                
                await conn.commit()
                return True
    
    
    async def update_user_talk_style(
        self,
        user_id: str,
        talk_style: str
    ) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM users WHERE id = %s AND leaved = FALSE", (user_id, ))
                result = await cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="User not found"
                    )
                await cur.execute(
                    "UPDATE users SET talk_style = %s WHERE id = %s",
                    (talk_style, user_id)
                )
                
                await cur.execute(
                    "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (user_id, )
                )
                
                await cur.execute("SELECT * FROM users WHERE id = %s", (id, ))
                user_row = await cur.fetchone()
                columns = [col[0] for col in cur.description]
                
                if user_row:
                    placeholders = ', '.join(['%s'] * len(columns))
                    columns_sql = ', '.join(columns)
                    insert_history = f"""
                    INSERT INTO users_history ({columns_sql})
                    VALUES ({placeholders})
                    """
                    await cur.execute(insert_history, user_row)
                    
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
                await cur.execute("SELECT 1 FROM users WHERE id = %s AND leaved = FALSE", (id,))
                result = await cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="User not found"
                    )
                
                column_map = {
                    "marketing_agree": "marketing_agree",
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
                
                # updated_at 필드 업데이트
                await cur.execute(
                    "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (id,)
                )
                
                await cur.execute("SELECT * FROM users WHERE id = %s", (id, ))
                user_row = await cur.fetchone()
                columns = [col[0] for col in cur.description]
                
                if user_row:
                    placeholders = ', '.join(['%s'] * len(columns))
                    columns_sql = ', '.join(columns)
                    insert_history = f"""
                    INSERT INTO users_history ({columns_sql})
                    VALUES ({placeholders})
                    """
                    await cur.execute(insert_history, user_row)
                
                await conn.commit()
                return True


    async def update_user_self_introduction(
        self,
        user_id: str,
        user_self_introduction: str,
    ) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM users WHERE id = %s AND leaved = FALSE", (user_id,))
                result = await cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="User not found"
                    )
                
                await cur.execute(
                    "UPDATE users SET self_introduction = %s WHERE id = %s",
                    (user_self_introduction, user_id)
                )
                
                # updated_at 필드 업데이트
                await cur.execute(
                    "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (user_id,)
                )
                
                await cur.execute("SELECT * FROM users WHERE id = %s", (user_id, ))
                user_row = await cur.fetchone()
                columns = [col[0] for col in cur.description]
                
                if user_row:
                    placeholders = ', '.join(['%s'] * len(columns))
                    columns_sql = ', '.join(columns)
                    insert_history = f"""
                    INSERT INTO users_history ({columns_sql})
                    VALUES ({placeholders})
                    """
                    await cur.execute(insert_history, user_row)

                await conn.commit()
                return True


    async def fetch_user_profile(self, user_id: str) -> UserDetailResponse | None:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                user_query = """
                SELECT
                        id, fcm, nickname, birthday, relation, position,
                        country, age, height, weight, hashtags, self_introduction,
                        talk_style, leaved,
                        personal_chat_alarm_agree, group_chat_alarm_agree,
                        post_comment_alarm_agree, post_like_alarm_agree,
                        last_connected_at,
                        latitude, longitude
                FROM users
                WHERE id = %s AND leaved = FALSE
                """
                await cur.execute(user_query, (user_id,))
                user_row = await cur.fetchone()

                if not user_row:
                    return {}

                (
                    id, fcm, nickname, birthday, relation, position,
                    country, age, height, weight, hashtags_json, self_introduction,
                    talk_style, leaved,
                    personal_chat_alarm, group_chat_alarm,
                    post_comment_alarm, post_like_alarm,
                    last_connected_at,
                    latitude, longitude
                ) = user_row
                
                hashtags = Hashtags.parse_raw(hashtags_json)
                
                # 차단된 사용자 목록 조회
                block_user_query = """
                SELECT blocked_user_id FROM user_block_list WHERE block_user_id = %s
                """
                await cur.execute(block_user_query, (user_id,))
                block_user_list = [row[0] for row in await cur.fetchall()]

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
                profile_images = [row[1] for row in images]

                return UserDetailResponse(
                    id=id,
                    fcm=fcm,
                    nickname=nickname,
                    birthday=birthday,
                    relation=relation,
                    position=position,
                    country=country,
                    age=age,
                    height=height,
                    weight=weight,
                    hashtags=hashtags,
                    selfIntroduction=self_introduction,
                    talkStyle=talk_style,
                    profileImages=profile_images,   
                    leaved=leaved,
                    personalChatAlarm=personal_chat_alarm,
                    groupChatAlarm=group_chat_alarm,
                    postCommentAlarm=post_comment_alarm,
                    postLikeAlarm=post_like_alarm,
                    blockUserList=block_user_list,
                    lastConnectedAt=last_connected_at,
                    latitude=latitude,
                    longitude=longitude
                )

    
    async def block_user(self, id: str, user_id: str) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM users WHERE id = %s AND leaved = FALSE", (id,))
                result = await cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="User not found"
                    )
                
                await cur.execute ("SELECT 1 FROM users WHERE id = %s AND leaved = FALSE", (user_id,))
                result = await cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="Blocked user not found"
                    )
                
                await cur.execute(
                    "INSERT INTO user_block_list (block_user_id, blocked_user_id) VALUES (%s, %s)",
                    (id, user_id)
                )
                
                # updated_at 필드 업데이트
                await cur.execute(
                    "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (id,)
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
                await cur.execute("SELECT 1 FROM users WHERE id = %s AND leaved = FALSE", (reportUserId,))
                result = await cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="Reporting user not found"
                    )
                
                await cur.execute("SELECT 1 FROM users WHERE id = %s AND leaved = FALSE", (reportedUserId,))
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
                
                # updated_at 필드 업데이트
                await cur.execute(
                    "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (reportUserId,)
                )
                 
                await conn.commit()
                return True
            
    # TODO : 쿼리문 IN구문 별로 좋다고 하지 않으셨는데, 쿼리문 나중에 짤때 최적화 잘해야함.
    async def fetch_user_list(
        self,
        user_id_list: List[str]
    ) -> List[UserDetailResponse]:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                if not user_id_list:
                    return []

                placeholders = ', '.join(['%s'] * len(user_id_list))

                query = f"""
                    SELECT 
                        id, fcm, nickname, birthday, age, height, weight, 
                        relation, position, country, hashtags, self_introduction, leaved, talk_style,
                        personal_chat_alarm_agree, group_chat_alarm_agree,
                        post_comment_alarm_agree, post_like_alarm_agree,
                        last_connected_at,
                        latitude, longitude
                    FROM users
                    WHERE id IN ({placeholders}) AND leaved = FALSE
                """
                await cur.execute(query, tuple(user_id_list))
                rows = await cur.fetchall()
                user_profiles = []

                for row in rows:
                    (
                        id, fcm, nickname, birthday, age, height, weight,
                        relation, position, country, hashtags_json, self_introduction, leaved, talk_style,
                        personal_chat_alarm, group_chat_alarm,
                        post_comment_alarm, post_like_alarm,
                        last_connected_at,
                        latitude, longitude
                    ) = row
                    
                    hashtags = Hashtags.parse_raw(hashtags_json)
                    
                    # blockUserList 조회
                    block_user_query = """
                        SELECT blocked_user_id FROM user_block_list WHERE block_user_id = %s
                    """
                    await cur.execute(block_user_query, (id,))
                    block_user_list = [row[0] for row in await cur.fetchall()]
                    
                    # 프로필 이미지 조회
                    image_query = """
                        SELECT
                            `index`, url
                        FROM user_images
                        WHERE 
                            user_id = %s and use_yn = TRUE
                        ORDER BY `index`
                        """
                    await cur.execute(image_query, (id,))
                    images = await cur.fetchall()
                    profile_images = [row[1] for row in images]
         
                    user_profiles.append(UserDetailResponse(
                        id=id,
                        fcm=fcm,
                        nickname=nickname,
                        birthday=birthday,
                        age=age,
                        height=height,
                        weight=weight,
                        relation=relation,
                        position=position,
                        country=country,
                        hashtags=hashtags,
                        selfIntroduction=self_introduction,
                        talkStyle=talk_style,
                        profileImages=profile_images,   
                        leaved=leaved,
                        personalChatAlarm=personal_chat_alarm,
                        groupChatAlarm=group_chat_alarm,
                        postCommentAlarm=post_comment_alarm,
                        postLikeAlarm=post_like_alarm,
                        blockUserList=block_user_list,
                        lastConnectedAt=last_connected_at,
                        latitude=latitude,
                        longitude=longitude
                    ))
                return user_profiles

    # TODO : 쿼리문 걸리는 WHERE절에 index를 거는게 좋아보인다고함. 나중에라도 걸어보세요. 
    # TODO : python 툴 찾아보기
    async def fetch_user_id_list(
        self,
        position: str,
        relation: str,
        talk_style: str
    ) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                
                # relation, talk_style 파싱
                position = [p.strip() for p in position.split(",")] if position else []
                relation = [r.strip() for r in relation.split(",")] if relation else []
                talk_style = [t.strip() for t in talk_style.split(",")] if talk_style else []
                
                query = """
                    SELECT id
                    FROM users
                    WHERE leaved = FALSE
                """
                
                # query문을 execute하기 위한 arguments와 필터링을 수행할 filters 리스트
                arguments = []
                filters = []

                # position이 존재한다면, FIND_IN_SET을 사용한 position 필터링
                if position:
                    position_filter = []
                    for p in position:
                        position_filter.append("FIND_IN_SET(%s, position)")
                        arguments.append(p)
                    # position이 여러개일 경우 OR 조건인 한 문장으로 filters에 추가
                    # 예: FIND_IN_SET(%s, position) OR FIND_IN_SET(%s, position)
                    filters.append(f"({' OR '.join(position_filter)})")
                    
                # relation이 존재한다면, FIND_IN_SET을 사용한 relation 필터링
                if relation:
                    relation_filter = []
                    for r in relation:
                        relation_filter.append("FIND_IN_SET(%s, relation)")
                        arguments.append(r)
                    # relation이 여러개일 경우 OR 조건인 한 문장으로 filters에 추가
                    # 예: FIND_IN_SET(%s, relation) OR FIND_IN_SET(%s, relation)
                    filters.append(f"({' OR '.join(relation_filter)})")

                # talk_style이 존재한다면, talk_style 필터링
                if talk_style:
                    talk_style_filter = []
                    for t in talk_style:
                        talk_style_filter.append("talk_style = %s")
                        arguments.append(t)
                    # talk_style이 여러개일 경우 OR 조건인 한 문장으로 filters에 추가
                    # 예: talk_style = %s OR talk_style = %s
                    filters.append(f"({' OR '.join(talk_style_filter)})")

                # 둘다 존재한다면 AND (FIND_IN_SET(%s, relation)) AND (talk_style = %s)
                if filters:
                    query += " AND " + " AND ".join(filters)

                await cur.execute(query, arguments)
                rows = await cur.fetchall()
                user_id_list = [row[0] for row in rows]
                return user_id_list


    async def fetch_near_user_id_list(
        self,
        user_id: str,
        relation: str,
        talk_style: str
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                
                # relation, talk_style 파싱
                relation = [r.strip() for r in relation.split(",")] if relation else []
                talk_style = [t.strip() for t in talk_style.split(",")] if talk_style else []

                # 1. 사용자가 존재하는지, 존재한다면 위도와 경도값이 있는지 -> 없으면 return False
                await cur.execute(
                    """
                    SELECT 1 
                    FROM users 
                    WHERE id = %s AND leaved = FALSE
                    """, (user_id,)
                    )

                result = await cur.fetchone()

                # 사용자가 없으면
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="탈퇴하거나 존재하지 않는 사용자입니다."
                    )

                # 2. 가져온 user_id를 가지고 위도와 경도값을 가져온다.
                await cur.execute(
                    """
                    SELECT latitude, longitude 
                    FROM users 
                    WHERE id = %s
                    """, (user_id,)
                    )
                
                user_location = await cur.fetchone()

                # 사용자의 위도와 경도값이 없으면 빈 리스트를 반환
                if not user_location or None in user_location:
                    return []

                lat, lng = user_location
                
                # 3. 위도 경도값이 없는 사용자를 제외한 사용자와의 거리를 계산해 가까운 순으로 정렬한다.
                # 3-1. 만약 필터링이 있다면, 필터링을 적용해서 정렬한다.
                query = """
                    SELECT id,
                        (6371 * acos(
                            cos(radians(%s)) * cos(radians(latitude)) *
                            cos(radians(longitude) - radians(%s)) +
                            sin(radians(%s)) * sin(radians(latitude))
                        )) AS distance
                    FROM users
                    WHERE leaved = FALSE
                        AND latitude IS NOT NULL 
                        AND longitude IS NOT NULL
                        AND id != %s
                """
                arguments = [lat, lng, lat, user_id]
                filters = []
                
                if relation:
                    relation_filter = []
                    for r in relation:
                        relation_filter.append("FIND_IN_SET(%s, relation)")
                        arguments.append(r)
                    filters.append(f"({' OR '.join(relation_filter)})")
                
                if talk_style:
                    talk_style_filter = []
                    for t in talk_style:
                        talk_style_filter.append("talk_style = %s")
                        arguments.append(t)
                    filters.append(f"({' OR '.join(talk_style_filter)})")
                
                if filters:
                    query += " AND " + " AND ".join(filters)
                # 거리를 기준으로 오름차순 정렬
                query += " ORDER BY distance"

                await cur.execute(query, arguments)
                rows = await cur.fetchall()
                
                # response는 {"userId": user_id, "distance": distance, 소수점 7자리까지}
                distance_user_list = [row[0] for row in rows]
                
                # TODO: 위치정보가 없는 사람들도 그냥 필터링만 해서 보내주는지 논의 필요.
                # 4. 위치 정보 없는 사용자를 추가한 list
                
                # latitude와 longitude가 null인 사용자를 가져오는 쿼리문
                null_query = """
                    SELECT id
                    FROM users
                    WHERE leaved = FALSE
                        AND (latitude IS NULL OR longitude IS NULL)
                        AND id != %s
                """
                
                null_arguments = [user_id]
                null_filters = []
                
                # 기존의 필터링 그대로
                if relation:
                    null_relation_filter = []
                    for r in relation:
                        null_relation_filter.append("FIND_IN_SET(%s, relation)")
                        null_arguments.append(r)
                    null_filters.append(f"({' OR '.join(null_relation_filter)})")
                    
                if talk_style:
                    null_talk_style_filter = []
                    for t in talk_style:
                        null_talk_style_filter.append("talk_style = %s")
                        null_arguments.append(t)
                    null_filters.append(f"({' OR '.join(null_talk_style_filter)})")

                if null_filters:
                    null_query += " AND " + " AND ".join(null_filters)

                await cur.execute(null_query, null_arguments)
                null_rows = await cur.fetchall()
                
                # null_rows에서 userId와 None 거리를 가진 리스트 생성, {"userId": user_id, "distance": null}
                null_user_list = [row[0] for row in null_rows]
                
                # 두개의 리스트를 합해서 반환, 거리가 있는 것 우선
                return distance_user_list + null_user_list
                
    
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
                    WHERE id IN ({placeholders}) AND leaved = FALSE
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
                await cur.execute("SELECT 1 FROM users WHERE id = %s AND leaved = FALSE", (id,))
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
                
                # updated_at 필드 업데이트
                await cur.execute(
                    "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (id,)
                )
                
                await cur.execute("SELECT * FROM users WHERE id = %s", (id, ))
                user_row = await cur.fetchone()
                columns = [col[0] for col in cur.description]
                
                if user_row:
                    placeholders = ', '.join(['%s'] * len(columns))
                    columns_sql = ', '.join(columns)
                    insert_history = f"""
                    INSERT INTO users_history ({columns_sql})
                    VALUES ({placeholders})
                    """
                    await cur.execute(insert_history, user_row)
                
                await conn.commit()
                return True


    async def user_health_check(
        self,
        user_id: str,
        user_latitude: Optional[float],
        user_longitude: Optional[float],
    ) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                query = """
                    SELECT 1 FROM users
                    WHERE id = %s AND leaved = FALSE
                """
                await cur.execute(query, (user_id,))
                result = await cur.fetchone()
                
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="존재하지 않는 유저입니다."
                    )
                    
                health_query = """
                    UPDATE users
                    SET last_connected_at = CURRENT_TIMESTAMP,
                        latitude = %s,
                        longitude = %s
                    WHERE id = %s
                """
                await cur.execute(health_query, (user_latitude, user_longitude, user_id))
                await conn.commit()
                return True


    async def update_user_images(
        self,
        user_id: str,
        image_index: Optional[List[str]] = None,
        image: Optional[List[UploadFile]] = None
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM users WHERE id = %s AND leaved = FALSE", (user_id,))
                result = await cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="User not found"
                    )

                await cur.execute(
                    "SELECT url FROM user_images WHERE user_id = %s AND use_yn = TRUE ORDER BY `index`",
                    (user_id,)
                )
                rows = await cur.fetchall()
                origin_image_urls = [r[0] for r in rows]
                
                if image_index:
                    if len(image_index) == 1 and "," in image_index[0]:
                        image_index = image_index[0].split(",")
                else:
                    image_index = []
                image_index = [url.strip() for url in image_index]
                
                keep_images = [url for url in image_index if url in origin_image_urls]
                remove_images = [url for url in origin_image_urls if url not in image_index]
                
                if remove_images:
                    for url in remove_images:
                        await cur.execute(
                            """
                            UPDATE user_images
                            SET use_yn = FALSE
                            WHERE user_id = %s AND url = %s
                            """,
                            (user_id, url)
                        )
                
                    
                for idx, url in enumerate(keep_images):
                    await cur.execute(
                        """
                        UPDATE user_images
                        SET `index` = %s
                        WHERE user_id = %s AND url = %s
                        """,
                        (idx, user_id, url)
                    )
                
                start_index = len(keep_images)
                if image:
                    for idx, file in enumerate(image):
                        now = datetime.now().strftime("%Y%m%d_%H%M%S%f")[:-3]
                        extension = file.filename.split(".")[-1] or "jpg"
                        filename = f"{now}.{extension}"
                        s3_key = f"user_profile/{user_id}/"
                        
                        file.file.seek(0)
                        if not upload_file_to_s3(file.file, s3_key, filename):
                            raise HTTPException(
                                status_code=500,
                                detail=f"Failed to upload image {file.filename} to S3"
                            )
                        
                        image_url = f"{CLOUDFRONT_URL}/{s3_key}{filename}"        
                        await cur.execute(
                            """
                            INSERT INTO user_images (user_id, `index`, url, use_yn)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (user_id, start_index + idx, image_url, True)
                        )
                
                image_query = """
                    SELECT url 
                    FROM user_images 
                    WHERE user_id = %s AND use_yn = TRUE
                    ORDER BY `index`
                """
                await cur.execute(image_query, (user_id,))
                rows = await cur.fetchall()
                image_url_list = [row[0] for row in rows]
                if not image_url_list:
                    raise HTTPException(
                        status_code=404,
                        detail="No images found for user"
                    )

                # updated_at 필드 업데이트
                await cur.execute(
                    "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (user_id,)
                )
                
                
                await cur.execute("SELECT * FROM users WHERE id = %s", (user_id, ))
                user_row = await cur.fetchone()
                columns = [col[0] for col in cur.description]
                
                if user_row:
                    columns.append("image_list")
                    user_row = list(user_row) + [",".join(image_url_list)]
                    placeholders = ', '.join(['%s'] * len(columns))
                    columns_sql = ', '.join(columns)
                    insert_history = f"""
                    INSERT INTO users_history ({columns_sql})
                    VALUES ({placeholders})
                    """
                    await cur.execute(insert_history, user_row)

                await conn.commit()
                return image_url_list
