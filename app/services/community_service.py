from fastapi import UploadFile, HTTPException
from datetime import datetime
from app.utils.s3_upload import upload_file_to_s3
from app.routers.image import generate_filename
# from app.db.community import 
from app.db.db_connection import db
from typing import List, Optional
from sqlalchemy import text
from PIL import Image
import io, uuid


class CommunityService:
    def __init__(self):
        self.db = db
    
    # TODO : post_id를 uuid로 생성해서 넣기.
    async def create_post(
        self,
        user_id: str,
        title: str,
        content: str,
        images: Optional[List[UploadFile]] = []
    ) -> Optional[str]:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()
                    
                    post_id = str(uuid.uuid4())
                    # 게시글 등록
                    insert_sql = """
                        INSERT INTO posts (
                            post_id, user_id, title, content
                        ) VALUES (
                            %s, %s, %s, %s
                        )
                    """
                    
                    await cur.execute(insert_sql, (post_id, user_id, title, content))
                    
                    if images:
                        for idx, file in enumerate(images):
                            
                            if not file:
                                continue
                            
                            s3_key = f"https://gik-profile.couplematch.co.kr/community/{post_id}/"
                            str_filename = generate_filename(file.filename)
                            
                            file.file.seek(0)
                            image_bytes=file.file.read()
                            origin_file=io.BytesIO(image_bytes)
                            
                            if not upload_file_to_s3(origin_file, s3_key, str_filename):
                                raise HTTPException(
                                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                    detail=f"Failed to upload image {file.filename} to S3"
                                )
                            
                            if idx == 0:
                                image=Image.open(io.BytesIO(image_bytes))
                                image.thumbnail((200, 200))
                                thumb_io = io.BytesIO()
                                image_format = image.format if image.format else "JPG"
                                image.save(thumb_io, format=image_format)
                                thumb_io.seek(0)
                                
                                thumbnail_s3_key = f"community/{post_id}/thumbnail/"
                                thumbnail_filename = f"{post_id}_thumbnail.jpg"
                                if not upload_file_to_s3(thumb_io, thumbnail_s3_key, thumbnail_filename):
                                    raise HTTPException(
                                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                        detail=f"Failed to upload thumbnail for {file.filename} to S3"
                                    )
                                    
                            await cur.execute(
                                """
                                INSERT INTO post_images (
                                    post_id, user_id, `index`, url, use_yn
                                ) VALUES (
                                    %s, %s, %s, %s, %s
                                )
                                """,
                                (post_id, user_id, idx, f"{s3_key}{str_filename}", True)
                            )
                    await conn.commit()
                    return post_id
                        
                except Exception as e:
                    await conn.rollback()
                    print(f"Error Creating Post: {e}")
                    return None
                                
    
    async def edit_post(
        self,
        post_id: str,
        user_id: str,
        title: str,
        content: str,
        images: List[UploadFile] = []
    ) -> bool:
        try: 
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await conn.begin()
                    
                    edit_query = """
                    UPDATE posts
                    SET title = %s, content = %s, updated_at = %s
                    WHERE post_id = %s
                    """
                    
                    await cur.execute(edit_query, (title, content, datetime.now(), post_id))
                    
                    await cur.execute(
                        """
                        UPDATE post_images
                        SET use_yn = %s
                        WHERE post_id = %s
                        """
                        , (False, post_id)
                    )
                    
                    if images:
                        for idx, file in enumerate(images):
                            s3_key = f"community/{post_id}/"
                            str_filename = generate_filename(file.filename)
                            
                            file.file.seek(0)
                            image_bytes = file.file.read()
                            origin_file = io.BytesIO(image_bytes)
                            
                            if not upload_file_to_s3(origin_file, s3_key, str_filename):
                                raise HTTPException(
                                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                    detail=f"Failed to upload image {file.filename} to S3"
                                )
                            
                            if idx == 0:
                                image = Image.open(io.BytesIO(image_bytes))
                                image.thumbnail((200, 200))
                                thumb_io = io.BytesIO()
                                image_format = image.format if image.format else "JPG"
                                image.save(thumb_io, format=image_format)
                                thumb_io.seek(0)
                                
                                thumbnail_s3_key = f"community/{post_id}/thumbnail/"
                                thumbnail_filename = f"{post_id}_thumbnail.jpg"
                                
                                if not upload_file_to_s3(thumb_io, thumbnail_s3_key, thumbnail_filename):
                                    raise HTTPException(
                                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                        detail=f"Failed to upload thumbnail for {file.filename} to S3"
                                    )
                                    
                            await cur.execute(
                                """
                                INSERT INTO post_images (
                                    post_id, user_id, `index`, url, use_yn
                                ) VALUES (
                                    %s, %s, %s, %s, %s
                                )
                                """,
                                (post_id, user_id, idx, f"{s3_key}{str_filename}", True)
                            )
                            
                    await conn.commit()
                    return True
        except Exception as e:
            print(f"Error Editing Post: {e}")
            return False
            
    
    async def delete_post(self, post_id: str):
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await conn.begin()
                    
                    update_query = """
                    UPDATE posts
                    SET deleted = %s
                    WHERE post_id = %s
                    """
                    await cur.execute(update_query, (True, post_id))
                    
                    image_query = """
                    UPDATE post_images
                    SET use_yn = %s
                    WHERE post_id = %s
                    """
                    await cur.execute(image_query, (False, post_id))
                    
                    await conn.commit()
                    return True
        except Exception as e:
            print(f"Error Deleting Post: {e}")
            return False
    
    
    async def get_posts(self, index: int):
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    offset = (index - 1) * 20
                    query = """
                        SELECT post_id, user_id, title, content, created_at, updated_at
                        FROM posts
                        WHERE deleted = %s
                        ORDER BY created_at DESC
                        LIMIT 20 OFFSET %s
                    """
                    await cur.execute(query, (False, offset))
                    posts = await cur.fetchall()
                    
                    return posts
        except Exception as e:
            print(f"Error Fetching Posts: {e}")
            return None
    
    
