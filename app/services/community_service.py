from fastapi import UploadFile, HTTPException, status
from datetime import datetime
from app.utils.s3_upload import upload_file_to_s3, CLOUDFRONT_URL
from app.routers.image import generate_filename
# from app.db.community import 
from app.db.db_connection import db
from app.db.community import PostListResponse, CommentResponse, PostDetailResponse
from typing import List, Optional
from sqlalchemy import text
from PIL import Image
import io, uuid



class CommunityService:
    def __init__(self):
        self.db = db
    
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
                            
                            s3_key = f"community/{post_id}/"
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
                                (post_id, user_id, idx, f"{CLOUDFRONT_URL}/{s3_key}{str_filename}", True)
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
        url_list: List[str],
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
                        "SELECT url FROM post_images WHERE post_id = %s AND use_yn = %s",
                        (post_id, True)
                    )
                    
                    # 기존 이미지중 사용중인 이미지들
                    origin_images = await cur.fetchall()
                    origin_image_urls = [r[0] for r in origin_images]
                    
                    # 파싱, multipart/form-data로 넘어온 url_list가 하나의 문자열로 넘어올 수 있음
                    if len(url_list) == 1 and "," in url_list[0]:
                        url_list = url_list[0].split(",")
                    url_list = [url.strip() for url in url_list]
                    
                    # 유지할 이미지와 제거할 이미지만 구분
                    keep_images = [url for url in url_list if url in origin_image_urls]
                    remove_images = [url for url in origin_image_urls if url not in url_list]

                    
                    # 제거할 이미지에 대해 use_yn을 False로 업데이트
                    if remove_images:
                        for url in remove_images:
                            await cur.execute(
                                """
                                UPDATE post_images
                                SET use_yn = %s
                                WHERE post_id = %s AND url = %s
                                """,
                                (False, post_id, url)
                            )
                    
                    # 유지한 이미지들의 index 재정렬
                    for idx, url in enumerate(url_list):
                        await cur.execute(
                            """
                            UPDATE post_images
                            SET `index` = %s
                            WHERE post_id = %s AND url = %s
                            """,
                            (idx, post_id, url)
                        )
                    # 새로 추가된 이미지를 업로드
                    start_index = len(url_list)
                    
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
                                (post_id, user_id, start_index + idx, f"{CLOUDFRONT_URL}/{s3_key}{str_filename}", True)
                            )
                            
                    await conn.commit()
                    return True
        except Exception as e:
            print(f"Error Editing Post: {e}")
            return False
            
    
    async def delete_post(self, post_id: str, user_id: str) -> bool:
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
    
    
    async def get_posts(self, page: int) -> List[PostDetailResponse]:
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    offset = (page - 1) * 20
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
                        
                        posts.append(PostListResponse(
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


    
    
    async def get_post_detail(self, post_id: str) -> Optional[PostDetailResponse]:
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    
                    if not post_id:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="게시글을 조회할 수 없습니다."
                        )
                    
                    # 게시글 기본 정보 쿼리
                    query = """
                        SELECT post_id, user_id, title, content, view_count, anonymous, created_at
                        FROM posts
                        WHERE post_id = %s AND deleted = %s
                    """
                    await cur.execute(query, (post_id, False))
                    row = await cur.fetchone()
                    
                    if not row:
                        return None
                    (
                        post_id,
                        user_id,
                        title,
                        content,
                        view_count,
                        anonymous,
                        created_at
                    ) = row
                    
                    # 게시글 이미지 쿼리 
                    image_query = """
                        SELECT url
                        FROM post_images
                        WHERE post_id = %s AND use_yn = %s
                        ORDER BY `index`
                    """
                    await cur.execute(image_query, (post_id, True))
                    image_rows = await cur.fetchall()
                    image_urls = [r[0] for r in image_rows]
                    
                    # 게시글에 좋아요를 누른 유저 id 조회 쿼리
                    like_query = """
                        SELECT user_id
                        FROM post_likes
                        WHERE post_id = %s
                    """
                    await cur.execute(like_query, (post_id,))
                    like_rows = await cur.fetchall()
                    like_user_ids = [r[0] for r in like_rows]
                    like_count = len(like_user_ids)
                    
                    # 댓글 쿼리
                    comment_query = """
                        SELECT id, user_id, content, created_at
                        FROM post_comments
                        WHERE post_id = %s AND deleted = FALSE
                        ORDER BY created_at ASC
                    """
                    await cur.execute(comment_query, (post_id,))
                    comment_rows = await cur.fetchall()
                    comments: List[CommentResponse] = []

                    for comment_row in comment_rows:
                        (
                            comment_id,
                            comment_user_id,
                            comment_content,
                            comment_created_at                     
                        ) = comment_row

                        # 댓글 좋아요 수 조회
                        comment_like_query = """
                            SELECT COUNT(*)
                            FROM post_comment_likes
                            WHERE comment_id = %s
                        """
                        await cur.execute(comment_like_query, (comment_id,))
                        comment_like_count = (await cur.fetchone())[0]

                        comments.append(CommentResponse(
                            id=comment_id,
                            userId=comment_user_id,
                            content=comment_content,
                            likeCount=comment_like_count,
                            createdAt=comment_created_at.strftime("%Y-%m-%d %H:%M:%S")
                        ))
                    
                    # 조회수 쿼리, 상세보기시 조회수 + 1
                    view_query = """
                        UPDATE posts
                        SET view_count = view_count + 1
                        WHERE post_id = %s
                    """
                    await cur.execute(view_query, (post_id,))
                    
                    return PostDetailResponse(
                        id=post_id,
                        userId=user_id,
                        title=title,
                        content=content,
                        viewCount=view_count,
                        likeCount=like_count,
                        images=image_urls,
                        comments=comments,
                        likeUserIds=like_user_ids,
                        anonymous=anonymous,
                        createdAt=created_at.strftime("%Y-%m-%d %H:%M:%S")
                    )
        except Exception as e:
            print(f"Error Fetching Post Detail: {e}")
            return None


    async def search_posts(self, search: str) -> List[PostListResponse]:
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    search_query = """
                        SELECT post_id, user_id, title, content, view_count, anonymous, created_at
                        FROM posts
                        WHERE (title LIKE %s OR content LIKE %s) AND deleted = %s
                        ORDER BY created_at DESC
                    """
                    search_param = f"%{search}%"
                    await cur.execute(search_query, (search_param, search_param, False))
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
                        
                        posts.append(PostListResponse(
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
            print(f"Error Searching Posts: {e}")
            return []
        
    
    async def like_post(self, userId, postId):
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await conn.begin()
                    
                    is_user="""
                        SELECT id FROM users WHERE id = %s
                    """
                    await cur.execute(is_user, (userId,))
                    user_row = await cur.fetchone()
                    if not user_row:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="존재하지 않는 사용자입니다."
                        )
                    
                    check_like = """
                        SELECT user_id FROM post_likes WHERE post_id = %s AND user_id = %s
                    """
                    await cur.execute(check_like, (postId, userId))
                    existing_like = await cur.fetchone()
                    
                    if existing_like:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="이미 좋아요를 누른 게시글입니다."
                        )
                    
                    check_post = """
                        SELECT post_id FROM posts WHERE post_id = %s AND deleted = %s
                    """
                    await cur.execute(check_post, (postId, False))
                    post_row = await cur.fetchone()
                    if not post_row:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="존재하지 않거나 삭제된 게시글입니다."
                        )
                    
                    insert_like = """
                        INSERT INTO post_likes (post_id, user_id)
                        VALUES (%s, %s)
                    """
                    await cur.execute(insert_like, (postId, userId))
                    await conn.commit()
                    return True
        except Exception as e:
            print(f"Error Liking Post: {e}")
            return False
        
    
    async def cancel_post_like(self, userId, postId):
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await conn.begin()
                    
                    check_like = """
                        SELECT user_id FROM post_likes WHERE post_id = %s AND user_id = %s
                    """
                    await cur.execute(check_like, (postId, userId))
                    check_like = await cur.fetchone()
                    if not check_like:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="좋아요를 누르지 않은 게시글입니다."
                        )
                    
                    cancel_like = """  
                        DELETE FROM post_likes WHERE post_id = %s AND user_id = %s
                    """
                    await cur.execute(cancel_like, (postId, userId))
                    await conn.commit()
                    return True
        except Exception as e:
            print(f"Error Cancelling Post Like: {e}")
            return False


    async def block_post(self, user_id, post_id):
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await conn.begin()
                    
                    # 사용자가 있는지
                    check_user = """
                        SELECT id FROM users WHERE id = %s
                    """
                    await cur.execute(check_user, (user_id,))
                    user_row = await cur.fetchone()
                    if not user_row:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="존재하지 않는 사용자입니다."
                        )
                    
                    # 게시글이 있는지
                    check_post = """
                        SELECT post_id FROM posts WHERE post_id = %s AND deleted = %s
                    """
                    await cur.execute(check_post, (post_id, False))
                    post_row = await cur.fetchone()
                    if not post_row:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="존재하지 않거나 삭제된 게시글입니다."
                        )
                    
                    # 차단
                    block_query = """
                        INSERT INTO post_block_list (block_user_id, blocked_post_id)
                        VALUES (%s, %s)
                    """
                    await cur.execute(block_query, (user_id, post_id))
                    await conn.commit()
                    return True

        except Exception as e:
            print(f"Error Blocking Post: {e}")
            return False

    # TODO: 신고당한 게시글의 유저는 어떻게 처리할까. 백에서 처리? 프론트에서 처리?
    async def report_post(
        self,
        report_post_id: str,
        report_user_id: str,
        reason: str
    ):
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await conn.begin()
                    
                    # 사용자가 있는지
                    check_user = """
                        SELECT id FROM users WHERE id = %s
                    """
                    await cur.execute(check_user, (report_user_id,))
                    user_row = await cur.fetchone()
                    if not user_row:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="존재하지 않는 사용자입니다."
                        )
                    
                    # 게시글이 있는지, 게시글 작성자 ID를 같이 가져오기
                    check_post = """
                        SELECT post_id, user_id FROM posts WHERE post_id = %s AND deleted = %s
                    """
                    await cur.execute(check_post, (report_post_id, False))
                    post_row = await cur.fetchone()
                    if not post_row:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="존재하지 않거나 삭제된 게시글입니다."
                        )
                    
                    _, post_user_id = post_row
                    
                    # 이미 신고한 게시글인지 확인
                    check_report = """
                        SELECT * FROM post_reports
                        WHERE reported_post_id = %s AND report_user_id = %s
                    """
                    await cur.execute(check_report, (report_post_id, report_user_id))
                    check_report = await cur.fetchone()
                    if check_report:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="이미 신고한 게시글입니다."
                        ) 
                    
                    # 신고 등록
                    insert_query = """
                        INSERT INTO post_reports (
                            reported_post_id, 
                            reported_user_id,
                            report_user_id,
                            reason
                        )
                        VALUES (%s, %s, %s, %s)
                    """
                    await cur.execute(insert_query, (
                        report_post_id,
                        post_user_id,  # 신고당한 게시글의 유저 ID
                        report_user_id,
                        reason
                        ))
                    await conn.commit()
                    return True

        except Exception as e:
            await conn.rollback()
            print(f"Error Commenting Post: {e}")
            return False


    async def create_comment(
        self,
        post_id: str,
        user_id: str,
        content: str
    ) -> bool:
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await conn.begin()
                    
                    # 게시글이 있는지 확인
                    check_post = """
                        SELECT post_id FROM posts WHERE post_id = %s AND deleted = %s
                    """
                    await cur.execute(check_post, (post_id, False))
                    post_row = await cur.fetchone()
                    if not post_row:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="존재하지 않거나 삭제된 게시글입니다."
                        )
                    
                    # 댓글 작성
                    insert_query = """
                        INSERT INTO post_comments (post_id, user_id, content)
                        VALUES (%s, %s, %s)
                    """
                    await cur.execute(insert_query, (post_id, user_id, content))
                    
                    insert_history = """
                        INSERT INTO post_comments_history (post_id, user_id, content)
                        VALUES (%s, %s, %s)
                    """
                    await cur.execute(insert_history, (post_id, user_id, content))
                    
                    await conn.commit()
                    return True
        except Exception as e:
            await conn.rollback()
            print(f"Error Commenting Post: {e}")
            return False
    
    
    async def get_comments(
        self,
        post_id: str
    ):
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    # 게시글이 있는지 확인
                    check_post = """
                        SELECT post_id FROM posts WHERE post_id = %s AND deleted = %s
                    """
                    await cur.execute(check_post, (post_id, False))
                    post_row = await cur.fetchone()
                    if not post_row:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="존재하지 않거나 삭제된 게시글입니다."
                        )
                    
                    # 댓글 조회
                    comment_query = """
                        SELECT id, user_id, content, created_at
                        FROM post_comments
                        WHERE post_id = %s AND deleted = FALSE
                        ORDER BY created_at ASC
                    """
                    await cur.execute(comment_query, (post_id,))
                    comment_rows = await cur.fetchall()
                    
                    comments: List[CommentResponse] = []
                    
                    for comment_row in comment_rows:
                        (
                            comment_id,
                            comment_user_id,
                            comment_content,
                            comment_created_at                     
                        ) = comment_row

                        # 댓글 좋아요 수 조회
                        comment_like_query = """
                            SELECT COUNT(*)
                            FROM post_comment_likes
                            WHERE comment_id = %s
                        """
                        await cur.execute(comment_like_query, (comment_id,))
                        comment_like_count = (await cur.fetchone())[0]

                        comments.append(CommentResponse(
                            id=comment_id,
                            userId=comment_user_id,
                            content=comment_content,
                            likeCount=comment_like_count,
                            createdAt=comment_created_at.strftime("%Y-%m-%d %H:%M:%S")
                        ))
                    return comments
        except Exception as e:
            print(f"Error Fetching Comments: {e}")
            return False
        
    
    async def like_comment(self, user_id, comment_id) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()
                    
                    # 댓글이 있는지 확인
                    check_comment = """
                        SELECT id FROM post_comments WHERE id = %s AND deleted = %s
                    """
                    await cur.execute(check_comment, (comment_id, False))
                    comment_row = await cur.fetchone()
                    if not comment_row:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="존재하지 않거나 삭제된 댓글입니다."
                        )
                    
                    # 이미 좋아요를 누른 댓글인지 확인
                    check_like = """
                        SELECT user_id FROM post_comment_likes WHERE comment_id = %s AND user_id = %s
                    """
                    await cur.execute(check_like, (comment_id, user_id))
                    checking_like = await cur.fetchone()
                    
                    if checking_like:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="이미 좋아요를 누른 댓글입니다."
                        )
                    
                    # 댓글 좋아요 등록
                    insert_like = """
                        INSERT INTO post_comment_likes (comment_id, user_id)
                        VALUES (%s, %s)
                    """
                    await cur.execute(insert_like, (comment_id, user_id))
                    
                    await conn.commit()
                    return True
                except Exception as e:
                    await conn.rollback()
                    print(f"Error Liking Comment: {e}")
                    return False


    async def cancel_like_comment(self, user_id, comment_id) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()
                    
                    # 댓글이 있는지 확인
                    check_comment = """
                        SELECT id FROM post_comments WHERE id = %s AND deleted = %s
                    """
                    await cur.execute(check_comment, (comment_id, False))
                    comment_row = await cur.fetchone()
                    if not comment_row:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="존재하지 않거나 삭제된 댓글입니다."
                        )
                    
                    # 좋아요를 누른 댓글인지 확인
                    check_like = """
                        SELECT user_id FROM post_comment_likes WHERE comment_id = %s AND user_id = %s
                    """
                    await cur.execute(check_like, (comment_id, user_id))
                    checking_like = await cur.fetchone()
                    
                    if not checking_like:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="좋아요를 누르지 않은 댓글입니다."
                        )
                    
                    # 댓글 좋아요 취소
                    cancel_like = """
                        DELETE FROM post_comment_likes WHERE comment_id = %s AND user_id = %s
                    """
                    await cur.execute(cancel_like, (comment_id, user_id))
                    
                    await conn.commit()
                    return True
                except Exception as e:
                    await conn.rollback()
                    print(f"Error Cancelling Comment Like: {e}")
                    return False
                
    
    async def edit_comment(
        self,
        user_id: str,
        comment_id: int,
        content: str
    ) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()
                    
                    # 댓글이 있는지 확인
                    check_comment = """
                        SELECT id, user_id, post_id FROM post_comments WHERE id = %s AND deleted = %s
                    """
                    await cur.execute(check_comment, (comment_id, False))
                    comment_row = await cur.fetchone()
                    
                    if not comment_row:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="존재하지 않거나 삭제된 댓글입니다."
                        )
                    
                    _, existing_user_id, post_id = comment_row
                    
                    if existing_user_id != user_id:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="댓글 수정 권한이 없습니다."
                        )
                    
                    # 댓글 수정
                    update_query = """
                        UPDATE post_comments
                        SET content = %s, updated_at = %s
                        WHERE id = %s
                    """
                    await cur.execute(update_query, (content, datetime.now(), comment_id))
                    
                    # 히스토리 저장, post_id는 가져와야합니다.
                    insert_history = """
                        INSERT INTO post_comments_history (post_id, user_id, content)
                        VALUES (%s, %s, %s)
                    """
                    await cur.execute(insert_history, (comment_id, user_id, content))
                    
                    await conn.commit()
                    return True
                except Exception as e:
                    await conn.rollback()
                    print(f"Error Editing Comment: {e}")
                    return False


    async def delete_comment(
        self,
        user_id: str,
        comment_id: int
    ) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()
                    
                    # 댓글이 있는지 확인
                    check_comment = """
                        SELECT id, user_id FROM post_comments WHERE id = %s AND deleted = %s
                    """
                    await cur.execute(check_comment, (comment_id, False))
                    comment_row = await cur.fetchone()
                    
                    if not comment_row:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="존재하지 않거나 삭제된 댓글입니다."
                        )
                    
                    existing_comment_id, existing_user_id = comment_row
                    
                    if existing_user_id != user_id:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="댓글 삭제 권한이 없습니다."
                        )
                    
                    # 댓글 삭제
                    delete_query = """
                        UPDATE post_comments
                        SET deleted = %s
                        WHERE id = %s
                    """
                    await cur.execute(delete_query, (True, comment_id))
                    
                    await conn.commit()
                    return True
                except Exception as e:
                    await conn.rollback()
                    print(f"Error Deleting Comment: {e}")
                    return False


    async def get_my_posts(
        self,
        user_id: str
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()
                    
                    # 사용자가 있는지 확인
                    check_user = """
                        SELECT id FROM users WHERE id = %s
                    """
                    await cur.execute(check_user, (user_id,))
                    user_row = await cur.fetchone()
                    if not user_row:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="존재하지 않는 사용자입니다."
                        )
                        
                    # 사용자 게시글 조회
                    query = """
                        SELECT post_id, user_id, title, content, view_count, anonymous, created_at
                        FROM posts
                        WHERE user_id = %s AND deleted = %s
                        ORDER BY created_at DESC
                    """
                    await cur.execute(query, (user_id, False))
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
                        
                        posts.append(PostListResponse(
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
                    await conn.commit()
                    return posts
                except Exception as e:
                    await conn.rollback()
                    print(f"Error Fetching My Posts: {e}")
                    return []
                
    
    async def get_my_comments(
        self,
        user_id: str
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()
                    
                    # 사용자가 있는지 확인
                    check_user = """
                        SELECT id FROM users WHERE id = %s
                    """
                    await cur.execute(check_user, (user_id,))
                    user_row = await cur.fetchone()
                    if not user_row:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="존재하지 않는 사용자입니다."
                        )
                        
                    # 사용자 댓글 조회
                    query = """
                        SELECT id, post_id, user_id, content, created_at
                        FROM post_comments
                        WHERE user_id = %s AND deleted = %s
                        ORDER BY created_at DESC
                    """
                    await cur.execute(query, (user_id, False))
                    comment_rows = await cur.fetchall()
                    
                    comments: List[CommentResponse] = []
                    
                    for row in comment_rows:
                        (
                            comment_id,
                            post_id,
                            comment_user_id,
                            comment_content,
                            comment_created_at                     
                        ) = row

                        # 댓글 좋아요 수 조회
                        comment_like_query = """
                            SELECT COUNT(*)
                            FROM post_comment_likes
                            WHERE comment_id = %s
                        """
                        await cur.execute(comment_like_query, (comment_id,))
                        comment_like_count = (await cur.fetchone())[0]

                        comments.append(CommentResponse(
                            id=comment_id,
                            userId=comment_user_id,
                            content=comment_content,
                            likeCount=comment_like_count,
                            createdAt=comment_created_at.strftime("%Y-%m-%d %H:%M:%S")
                        ))
                        
                    await conn.commit()
                    return comments
                except Exception as e:
                    await conn.rollback()
                    print(f"Error Fetching My Comments: {e}")
                    return []
