from fastapi import UploadFile, HTTPException
from datetime import datetime
from app.utils.s3_upload import upload_file_to_s3
from app.routers.image import generate_filename
# from app.db.community import 
from app.db.db_connection import db
from app.db.community import PostDetailResponse
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

                    if not user_id:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="유저가 없습니다"
                        )
                    
                    
                    post_id = str(uuid.uuid4())
                    check_post = """
                        SELECT post_id FROM posts WHERE post_id = %s
                    """
                    await cur.execute(check_post, (post_id,))
                    existing_post = await cur.fetchone()
                    if existing_post:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="이미 존재하는 게시글 ID입니다."
                        )
                    
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
                    
                    check_user= """
                        SELECT user_id FROM posts WHERE post_id = %s and deleted = %s
                    """
                    await cur.execute(check_user, (post_id, False))
                    user_row = await cur.fetchone()
                    
                    if not user_row:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="존재하지 않거나 삭제된 게시글입니다."
                        )
                    
                    if user_row[0] != user_id:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="게시글 수정 권한이 없습니다."
                        )
                    
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
                    
                    check_user= """
                        SELECT user_id FROM posts WHERE post_id = %s and deleted = %s
                    """
                    await cur.execute(check_user, (post_id, False))
                    user_row = await cur.fetchone()
                    
                    if not user_row:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="존재하지 않거나 삭제된 게시글입니다."
                        )
                    
                    if user_row[0] != user_id:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="게시글 삭제 권한이 없습니다."
                        )
                        
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
    
    
    async def get_posts(self, index: int) -> List[PostDetailResponse]:
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    offset = (index - 1) * 20
                    query = """
                        SELECT post_id, user_id, title, content, view_count, anonymous, created_at
                        FROM posts
                        WHERE deleted = %s
                        ORDER BY created_at DESC
                        LIMIT 20 OFFSET %s
                    """
                    await cur.execute(query, (False, offset))
                    post_rows = await cur.fetchall()

                    posts = []

                    for row in post_rows:
                        (
                            post_id,
                            user_id,
                            title,
                            content,
                            view_count,
                            anonymous,
                            created_at
                        ) = row
                        
                        image_query = """
                            SELECT url
                            FROM post_images
                            WHERE post_id = %s AND use_yn = %s
                            ORDER BY `index`
                        """
                        await cur.execute(image_query, (post_id, True))
                        image_rows = await cur.fetchall()
                        image_urls = [r[0] for r in image_rows]

                        
                        like_query = """
                            SELECT user_id
                            FROM post_likes
                            WHERE post_id = %s
                        """
                        await cur.execute(like_query, (post_id,))
                        like_rows = await cur.fetchall()
                        like_user_ids = [r[0] for r in like_rows]

                        
                        comment_query = """
                            SELECT COUNT(*)
                            FROM post_comments
                            WHERE post_id = %s
                        """
                        await cur.execute(comment_query, (post_id,))
                        comment_count = (await cur.fetchone())[0]
                        
                        posts.append(PostDetailResponse(
                            id=post_id,
                            userId=user_id,
                            title=title,
                            content=content,
                            images=image_urls,
                            viewCount=view_count,
                            likeUserIds=like_user_ids,
                            commentCount=comment_count,
                            anonymous=anonymous,
                            createdAt=created_at.strftime("%Y-%m-%d %H:%M:%S")
                        ))

                    return posts
        except Exception as e:
            print(f"Error Fetching Posts: {e}")
            return []

    
    
