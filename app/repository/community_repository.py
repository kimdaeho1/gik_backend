from fastapi import UploadFile, HTTPException, status
from typing import List, Optional
from app.utils.logging_config import get_logger
import uuid


logger = get_logger(__name__)


class CommunityRepository:
    def __init__(self, db):
        self.db = db

    async def get_user(self, user_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id FROM users WHERE id = %s AND leaved = %s",
                    (user_id, False),
                )
                user_row = await cur.fetchone()
                return user_row[0]

    async def check_duplicate_post(self, post_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT post_id FROM posts WHERE post_id = %s",
                    (post_id,),
                )
                post_row = await cur.fetchone()
                return post_row

    async def insert_post(
        self,
        post_id: str,
        user_id: str,
        title: str,
        content: str,
        category: Optional[str],
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()
                    await cur.execute(
                        """
                        INSERT INTO posts(
                            post_id, user_id, title, content, category
                        )
                        VALUES(%s, %s, %s, %s, %s)
                        """,
                        (post_id, user_id, title, content, category),
                    )
                    await conn.commit()
                    await cur.close()
                    return True
                except Exception as e:
                    await conn.rollback()
                    logger.error(f"게시글 삽입 실패: {e}")
                    return False

    async def insert_post_images(
        self,
        post_id: str,
        user_id: str,
        index: int,
        url: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()
                    await cur.execute(
                        """
                        INSERT INTO post_images(
                            post_id, user_id, `index`, url, use_yn
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (post_id, user_id, index, url, True),
                    )
                    await conn.commit()
                    return True
                except Exception as e:
                    await conn.rollback()
                    logger.error(f"이미지 삽입 실패: {e}")
                    return False

    async def get_post_images(self, post_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT url
                    FROM post_images
                    WHERE post_id = %s AND use_yn = %s
                    ORDER BY `index`
                    """,
                    (post_id, True),
                )
                rows = await cur.fetchall()
                images = [url for (url,) in rows]
                return images

    async def create_post_history(
        self,
        post_id: str,
        user_id: str,
        title: str,
        content: str,
        image_list: Optional[str],
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()
                    await cur.execute(
                        """
                        INSERT INTO posts_history (
                            post_id, user_id, title, content, image_list
                        ) VALUES (%s, %s, %s, %s, %s)
                        """,
                        (post_id, user_id, title, content, image_list),
                    )
                    await conn.commit()
                    return True
                except Exception as e:
                    await conn.rollback()
                    logger.error(f"[Repository] posts_history 저장 실패: {e}")
                    return False

    async def edit_post(
        self,
        post_id: str,
        user_id: str,
        title: str,
        content: str,
        keep_images: List[str],
        new_image_urls: List[str],
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()

                    # 1) 게시글 존재 + 권한 체크
                    await cur.execute(
                        """
                        SELECT user_id 
                        FROM posts 
                        WHERE post_id = %s AND deleted = FALSE
                        """,
                        (post_id,),
                    )
                    row = await cur.fetchone()
                    if not row:
                        await conn.rollback()
                        return False
                    if row[0] != user_id:
                        await conn.rollback()
                        return False

                    # 2) 기존 이미지 조회
                    await cur.execute(
                        """
                        SELECT url 
                        FROM post_images
                        WHERE post_id = %s AND use_yn = TRUE
                        ORDER BY `index`
                        """,
                        (post_id,),
                    )
                    rows = await cur.fetchall()
                    existing_images = [r[0] for r in rows]

                    # 3) 제거 이미지 use_yn = FALSE
                    delete_list = [
                        url for url in existing_images if url not in keep_images
                    ]

                    if delete_list:
                        await cur.executemany(
                            """
                            UPDATE post_images
                            SET use_yn = FALSE
                            WHERE post_id = %s AND url = %s
                            """,
                            [(post_id, url) for url in delete_list],
                        )

                    # 4) 유지 이미지 index 재정렬
                    index_counter = 0
                    for url in keep_images:
                        await cur.execute(
                            """
                            UPDATE post_images
                            SET `index` = %s, use_yn = TRUE
                            WHERE post_id = %s AND url = %s
                            """,
                            (index_counter, post_id, url),
                        )
                        index_counter += 1

                    # 5) 새 이미지 insert
                    for url in new_image_urls:
                        await cur.execute(
                            """
                            INSERT INTO post_images(
                                post_id, user_id, `index`, url, use_yn
                            ) VALUES (%s, %s, %s, %s, TRUE)
                            """,
                            (post_id, user_id, index_counter, url),
                        )
                        index_counter += 1

                    # 6) posts 수정
                    await cur.execute(
                        """
                        UPDATE posts
                        SET title = %s, content = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE post_id = %s AND user_id = %s AND deleted = FALSE
                        """,
                        (title, content, post_id, user_id),
                    )

                    # 7) posts_history 저장
                    await cur.execute(
                        "SELECT * FROM posts WHERE post_id = %s",
                        (post_id,),
                    )
                    post_row = await cur.fetchone()
                    columns = [c[0] for c in cur.description]

                    combined_image_list = keep_images + new_image_urls
                    image_list = (
                        ", ".join(combined_image_list) if combined_image_list else None
                    )

                    if post_row:
                        columns.append("image_list")
                        post_row = list(post_row) + [image_list]

                        placeholders = ", ".join(["%s"] * len(columns))
                        column_sql = ", ".join(columns)

                        await cur.execute(
                            f"""
                            INSERT INTO posts_history ({column_sql})
                            VALUES ({placeholders})
                            """,
                            post_row,
                        )

                    await conn.commit()
                    return True

                except Exception as e:
                    await conn.rollback()
                    logger.error(f"게시글 수정 실패: {e}")
                    return False

    async def get_post_owner(self, post_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT user_id
                    FROM posts
                    WHERE post_id = %s AND deleted = %s
                    """,
                    (post_id, False),
                )
                return await cur.fetchone()

    async def delete_post(self, post_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()
                    await cur.execute(
                        """
                        UPDATE posts
                        SET deleted = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE post_id = %s
                        """,
                        (True, post_id),
                    )

                    await cur.execute(
                        """
                        UPDATE post_images
                        SET use_yn = %s
                        WHERE post_id = %s
                        """,
                        (False, post_id),
                    )
                    await conn.commit()
                    return True
                except Exception as e:
                    await conn.rollback()
                    logger.error(f"게시글 삭제 실패: {e}")
                    return False

    async def insert_post_history(self, post_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()

                    # 전체 row 가져오기
                    await cur.execute(
                        "SELECT * FROM posts WHERE post_id = %s",
                        (post_id,),
                    )
                    post_row = await cur.fetchone()
                    columns = [c[0] for c in cur.description]

                    if not post_row:
                        await conn.rollback()
                        return

                    placeholders = ", ".join(["%s"] * len(columns))
                    columns_sql = ", ".join(columns)

                    await cur.execute(
                        f"""
                        INSERT INTO posts_history ({columns_sql})
                        VALUES ({placeholders})
                        """,
                        post_row,
                    )
                    await conn.commit()
                except:
                    await conn.rollback()
                    raise

    async def get_posts(self, page: int, category: Optional[str] = None):
        offset = (page - 1) * 20

        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:

                base_query = """
                    SELECT
                        p.post_id,
                        p.user_id,
                        p.category,
                        p.title,
                        p.content,
                        p.is_admin,
                        p.view_count,
                        p.anonymous,
                        p.created_at,
                        COALESCE(
                            GROUP_CONCAT(DISTINCT img.url ORDER BY img.`index` SEPARATOR '||'),
                            ''
                        ) AS images,
                        COALESCE(
                            GROUP_CONCAT(DISTINCT l.user_id SEPARATOR '||'),
                            ''
                        ) AS like_user_ids,
                        COUNT(DISTINCT c.id) AS comment_count
                    FROM posts p
                    LEFT JOIN post_images img
                        ON p.post_id = img.post_id AND img.use_yn = TRUE
                    LEFT JOIN post_likes l
                        ON p.post_id = l.post_id
                    LEFT JOIN post_comments c
                        ON p.post_id = c.post_id AND c.deleted = FALSE
                    WHERE p.deleted = FALSE
                """

                params = []

                if category:
                    base_query += " AND p.category = %s "
                    params.append(category)

                base_query += """
                    GROUP BY p.post_id
                    ORDER BY p.created_at DESC
                    LIMIT 20 OFFSET %s
                """
                params.append(offset)

                await cur.execute(base_query, params)
                rows = await cur.fetchall()

                return rows

    async def get_post_detail(self, post_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:

                query = """
                    SELECT
                        p.post_id,
                        p.user_id,
                        p.category,
                        p.title,
                        p.content,
                        p.is_admin,
                        p.view_count,
                        p.anonymous,
                        p.created_at,
                        COALESCE(
                            GROUP_CONCAT(DISTINCT img.url ORDER BY img.`index` SEPARATOR '||'),
                            ''
                        ) AS images,
                        COALESCE(
                            GROUP_CONCAT(DISTINCT l.user_id SEPARATOR '||'),
                            ''
                        ) AS like_user_ids,
                        COUNT(DISTINCT c.id) AS comment_count
                    FROM posts p
                    LEFT JOIN post_images img
                        ON p.post_id = img.post_id AND img.use_yn = TRUE
                    LEFT JOIN post_likes l
                        ON p.post_id = l.post_id
                    LEFT JOIN post_comments c
                        ON p.post_id = c.post_id AND c.deleted = FALSE

                    WHERE p.post_id = %s AND p.deleted = FALSE
                    GROUP BY p.post_id
                """

                await cur.execute(query, (post_id,))
                data = await cur.fetchone()

                if not data:
                    return None

                (
                    post_id,
                    user_id,
                    category_val,
                    title,
                    content,
                    is_admin,
                    view_count,
                    anonymous,
                    created_at,
                    images,
                    like_user_ids,
                    comment_count,
                ) = data

                await cur.execute(
                    """
                    SELECT
                        c.id,
                        c.post_id,
                        c.user_id,
                        c.content,
                        c.anonymous,
                        c.created_at,
                        COUNT(cl.user_id) AS like_count
                    FROM post_comments c
                    LEFT JOIN post_comment_likes cl
                        ON c.id = cl.comment_id
                    WHERE c.post_id = %s AND c.deleted = FALSE
                    GROUP BY c.id
                    ORDER BY c.created_at ASC
                    """,
                    (post_id,),
                )
                comment_rows = await cur.fetchall()

                return {
                    "post_id": post_id,
                    "user_id": user_id,
                    "category": category_val,
                    "title": title,
                    "content": content,
                    "is_admin": is_admin,
                    "view_count": view_count,
                    "images": images.split("||") if images else [],
                    "like_user_ids": like_user_ids.split("||") if like_user_ids else [],
                    "comment_count": comment_count,
                    "comments": comment_rows,
                    "anonymous": anonymous,
                    "created_at": created_at,
                }

    async def search_posts(
        self,
        search: str,
        category: Optional[str] = None,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:

                search_param = f"%{search}%"

                base_query = """
                    SELECT
                        p.post_id,
                        p.user_id,
                        p.category,
                        p.title,
                        p.content,
                        p.is_admin,
                        p.view_count,
                        p.anonymous,
                        p.created_at,
                        COALESCE(
                            GROUP_CONCAT(DISTINCT img.url ORDER BY img.`index` SEPARATOR '||'),
                            ''
                        ) AS images,
                        COALESCE(
                            GROUP_CONCAT(DISTINCT l.user_id SEPARATOR '||'),
                            ''
                        ) AS like_user_ids,
                        COUNT(DISTINCT c.id) AS comment_count
                    FROM posts p
                    LEFT JOIN post_images img
                        ON p.post_id = img.post_id AND img.use_yn = TRUE
                    LEFT JOIN post_likes l
                        ON p.post_id = l.post_id
                    LEFT JOIN post_comments c
                        ON p.post_id = c.post_id AND c.deleted = FALSE

                    WHERE p.deleted = FALSE
                    AND (p.title LIKE %s OR p.content LIKE %s)
                """

                params = [search_param, search_param]

                if category:
                    base_query += " AND p.category = %s "
                    params.append(category)

                base_query += """
                    GROUP BY p.post_id
                    ORDER BY p.created_at DESC
                """

                await cur.execute(base_query, params)
                rows = await cur.fetchall()

                return rows

    async def like_post(self, user_id: str, post_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()

                    # 1) 사용자 존재 확인
                    await cur.execute(
                        "SELECT 1 FROM users WHERE id = %s AND leaved = FALSE",
                        (user_id,),
                    )
                    if not (await cur.fetchone()):
                        await conn.rollback()
                        return False

                    # 2) 기존 좋아요 여부 확인
                    await cur.execute(
                        "SELECT 1 FROM post_likes WHERE user_id = %s AND post_id = %s",
                        (user_id, post_id),
                    )
                    if await cur.fetchone():
                        await conn.rollback()
                        return False

                    # 3) 게시글 존재 확인
                    await cur.execute(
                        "SELECT 1 FROM posts WHERE post_id = %s AND deleted = FALSE",
                        (post_id,),
                    )
                    if not (await cur.fetchone()):
                        await conn.rollback()
                        return False

                    # 4) 좋아요 INSERT
                    await cur.execute(
                        """
                        INSERT INTO post_likes(user_id, post_id)
                        VALUES(%s, %s)
                        """,
                        (user_id, post_id),
                    )

                    # 5) updated_at 업데이트
                    await cur.execute(
                        """
                        UPDATE posts
                        SET updated_at = CURRENT_TIMESTAMP
                        WHERE post_id = %s
                        """,
                        (post_id,),
                    )

                    # 6) 기존 기능 호출 (posts_history 생성)
                    await self.insert_post_history(post_id)

                    await conn.commit()
                    return True

                except Exception as e:
                    await conn.rollback()
                    logger.error(f"게시글 좋아요 실패: {e}")
                    return False

    async def cancel_post_like(self, user_id: str, post_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()

                    # 1) 기존 좋아요 여부 확인
                    await cur.execute(
                        """
                        SELECT 1
                        FROM post_likes
                        WHERE user_id = %s AND post_id = %s
                        """,
                        (user_id, post_id),
                    )
                    exists = await cur.fetchone()
                    if not exists:
                        await conn.rollback()
                        return False

                    # 2) 좋아요 삭제
                    await cur.execute(
                        """
                        DELETE FROM post_likes
                        WHERE user_id = %s AND post_id = %s
                        """,
                        (user_id, post_id),
                    )

                    # 3) updated_at 업데이트
                    await cur.execute(
                        """
                        UPDATE posts
                        SET updated_at = CURRENT_TIMESTAMP
                        WHERE post_id = %s
                        """,
                        (post_id,),
                    )

                    # 4) history 저장
                    await self.insert_post_history(post_id)

                    await conn.commit()
                    return True

                except Exception as e:
                    await conn.rollback()
                    logger.error(f"게시글 좋아요 취소 실패: {e}")
                    return False

    async def block_post(self, user_id: str, post_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()

                    # 1) 사용자 존재 확인
                    await cur.execute(
                        """
                        SELECT 1
                        FROM users
                        WHERE id = %s AND leaved = FALSE
                        """,
                        (user_id,),
                    )
                    if not await cur.fetchone():
                        await conn.rollback()
                        return False

                    # 2) 게시글 존재 확인
                    await cur.execute(
                        """
                        SELECT 1
                        FROM posts
                        WHERE post_id = %s AND deleted = FALSE
                        """,
                        (post_id,),
                    )
                    if not await cur.fetchone():
                        await conn.rollback()
                        return False

                    # 3) 차단 처리
                    await cur.execute(
                        """
                        INSERT INTO post_block_list(block_user_id, blocked_post_id)
                        VALUES(%s, %s)
                        """,
                        (user_id, post_id),
                    )

                    await conn.commit()
                    return True

                except Exception as e:
                    await conn.rollback()
                    logger.error(f"게시글 차단 실패: {e}")
                    return False

    async def report_post(self, report_post_id: str, report_user_id: str, reason: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()

                    # 1) 사용자 존재 확인
                    await cur.execute(
                        """
                        SELECT 1
                        FROM users
                        WHERE id = %s AND leaved = FALSE
                        """,
                        (report_user_id,),
                    )
                    if not await cur.fetchone():
                        await conn.rollback()
                        return False

                    # 2) 게시글 존재 + 게시글 작성자 가져오기
                    await cur.execute(
                        """
                        SELECT user_id
                        FROM posts
                        WHERE post_id = %s AND deleted = FALSE
                        """,
                        (report_post_id,),
                    )
                    post_row = await cur.fetchone()
                    if not post_row:
                        await conn.rollback()
                        return False

                    post_user_id = post_row[0]

                    # 3) 신고 등록
                    await cur.execute(
                        """
                        INSERT INTO post_reports(
                            reported_post_id,
                            reported_user_id,
                            report_user_id,
                            reason
                        ) VALUES (%s, %s, %s, %s)
                        """,
                        (report_post_id, post_user_id, report_user_id, reason),
                    )

                    # 4) updated_at 업데이트
                    await cur.execute(
                        """
                        UPDATE posts
                        SET updated_at = CURRENT_TIMESTAMP
                        WHERE post_id = %s
                        """,
                        (report_post_id,),
                    )

                    await conn.commit()
                    return True

                except Exception as e:
                    await conn.rollback()
                    logger.error(f"게시글 신고 실패: {e}")
                    return False

    async def create_comment(self, post_id: str, user_id: str, content: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()

                    # 1) 게시글 존재 여부 확인
                    await cur.execute(
                        """
                        SELECT 1
                        FROM posts
                        WHERE post_id = %s AND deleted = FALSE
                        """,
                        (post_id,),
                    )
                    if not await cur.fetchone():
                        await conn.rollback()
                        return False

                    # 2) 댓글 INSERT
                    await cur.execute(
                        """
                        INSERT INTO post_comments(post_id, user_id, content)
                        VALUES(%s, %s, %s)
                        """,
                        (post_id, user_id, content),
                    )

                    # 3) 댓글 히스토리 INSERT
                    await cur.execute(
                        """
                        INSERT INTO post_comments_history(post_id, user_id, content)
                        VALUES (%s, %s, %s)
                        """,
                        (post_id, user_id, content),
                    )

                    await conn.commit()
                    return True

                except Exception as e:
                    await conn.rollback()
                    logger.error(f"댓글 생성 실패: {e}")
                    return False

    async def get_comments(self, post_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()

                    await cur.execute(
                        """
                        SELECT 1
                        FROM posts
                        WHERE post_id = %s AND deleted = FALSE
                        """,
                        (post_id,),
                    )
                    if not await cur.fetchone():
                        await conn.rollback()
                        return None

                    await cur.execute(
                        """
                        SELECT 
                            c.id,
                            c.post_id,
                            c.user_id,
                            c.content,
                            c.anonymous,
                            c.created_at,
                            COUNT(l.user_id) AS like_count
                        FROM post_comments c
                        LEFT JOIN post_comment_likes l
                            ON c.id = l.comment_id
                        WHERE c.post_id = %s
                            AND c.deleted = FALSE
                        GROUP BY c.id
                        ORDER BY c.created_at ASC
                        """,
                        (post_id,),
                    )
                    rows = await cur.fetchall()

                    return rows

                except Exception as e:
                    await conn.rollback()
                    logger.error(f"댓글 조회 실패: {e}")
                    return False

    async def like_comment(self, user_id: str, comment_id: str) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()

                    # 1) 댓글 존재 여부 확인
                    await cur.execute(
                        """
                        SELECT 1
                        FROM post_comments
                        WHERE id = %s AND deleted = FALSE
                        """,
                        (comment_id,),
                    )
                    if not await cur.fetchone():
                        await conn.rollback()
                        raise HTTPException(
                            status_code=404,
                            detail="존재하지 않거나 삭제된 댓글입니다.",
                        )

                    # 2) 이미 좋아요 눌렀는지 확인
                    await cur.execute(
                        """
                        SELECT 1
                        FROM post_comment_likes
                        WHERE user_id = %s AND comment_id = %s
                        """,
                        (user_id, comment_id),
                    )
                    if await cur.fetchone():
                        await conn.rollback()
                        raise HTTPException(
                            status_code=400,
                            detail="이미 좋아요를 누른 댓글입니다.",
                        )

                    # 3) 좋아요 등록
                    await cur.execute(
                        """
                        INSERT INTO post_comment_likes(comment_id, user_id)
                        VALUES(%s, %s)
                        """,
                        (comment_id, user_id),
                    )

                    # 4) updated_at 갱신
                    await cur.execute(
                        """
                        UPDATE post_comments
                        SET updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (comment_id,),
                    )

                    await conn.commit()
                    return True

                except Exception as e:
                    await conn.rollback()
                    logger.error(f"댓글 좋아요 실패: {e}")
                    return False

    async def cancel_like_comment(self, user_id: str, comment_id: str) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()

                    # 1) 댓글 존재 여부 확인
                    await cur.execute(
                        """
                        SELECT 1
                        FROM post_comments
                        WHERE id = %s AND deleted = FALSE
                        """,
                        (comment_id,),
                    )
                    if not await cur.fetchone():
                        await conn.rollback()
                        raise HTTPException(
                            status_code=404,
                            detail="존재하지 않거나 삭제된 댓글입니다.",
                        )

                    # 2) 좋아요를 누른 댓글인지 확인
                    await cur.execute(
                        """
                        SELECT 1
                        FROM post_comment_likes
                        WHERE comment_id = %s AND user_id = %s
                        """,
                        (comment_id, user_id),
                    )
                    if not await cur.fetchone():
                        await conn.rollback()
                        raise HTTPException(
                            status_code=404,
                            detail="좋아요를 누르지 않은 댓글입니다.",
                        )

                    # 3) 좋아요 취소
                    await cur.execute(
                        """
                        DELETE FROM post_comment_likes
                        WHERE comment_id = %s AND user_id = %s
                        """,
                        (comment_id, user_id),
                    )

                    # 4) updated_at 갱신
                    await cur.execute(
                        """
                        UPDATE post_comments
                        SET updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (comment_id,),
                    )

                    await conn.commit()
                    return True

                except Exception as e:
                    await conn.rollback()
                    logger.error(f"댓글 좋아요 취소 실패: {e}")
                    return False

    async def edit_comment(
        self,
        user_id: str,
        comment_id: int,
        content: str,
    ) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()

                    # 1) 댓글 존재 여부 + 작성자 확인
                    await cur.execute(
                        """
                        SELECT id, user_id, post_id
                        FROM post_comments
                        WHERE id = %s AND deleted = FALSE
                        """,
                        (comment_id,),
                    )
                    row = await cur.fetchone()

                    if not row:
                        await conn.rollback()
                        raise HTTPException(
                            status_code=404,
                            detail="존재하지 않거나 삭제된 댓글입니다.",
                        )

                    _, existing_user_id, post_id = row

                    # 2) 본인 댓글인지 확인
                    if existing_user_id != user_id:
                        await conn.rollback()
                        raise HTTPException(
                            status_code=403,
                            detail="댓글 수정 권한이 없습니다.",
                        )

                    # 3) 댓글 수정
                    await cur.execute(
                        """
                        UPDATE post_comments
                        SET content = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (content, comment_id),
                    )

                    # 4) 댓글 수정 history 저장
                    await cur.execute(
                        """
                        INSERT INTO post_comments_history(post_id, user_id, content)
                        VALUES (%s, %s, %s)
                        """,
                        (post_id, user_id, content),
                    )

                    await conn.commit()
                    return True

                except Exception as e:
                    await conn.rollback()
                    logger.error(f"댓글 수정 실패: {e}")
                    return False

    async def delete_comment(
        self,
        user_id: str,
        comment_id: int,
    ) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()

                    # 1) 댓글 존재 여부 + 작성자 확인
                    await cur.execute(
                        """
                        SELECT id, user_id
                        FROM post_comments
                        WHERE id = %s AND deleted = FALSE
                        """,
                        (comment_id,),
                    )
                    row = await cur.fetchone()

                    if not row:
                        await conn.rollback()
                        raise HTTPException(
                            status_code=404,
                            detail="존재하지 않거나 삭제된 댓글입니다.",
                        )

                    _, existing_user_id = row

                    # 2) 본인 댓글인지 확인
                    if existing_user_id != user_id:
                        await conn.rollback()
                        raise HTTPException(
                            status_code=403,
                            detail="댓글 삭제 권한이 없습니다.",
                        )

                    # 3) deleted = TRUE
                    await cur.execute(
                        """
                        UPDATE post_comments
                        SET deleted = TRUE,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (comment_id,),
                    )

                    await conn.commit()
                    return True

                except Exception as e:
                    await conn.rollback()
                    logger.error(f"댓글 삭제 실패: {e}")
                    return False

    async def get_my_posts(self, user_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 
                        p.post_id,
                        p.user_id,
                        p.category,
                        p.title,
                        p.content,
                        p.is_admin,
                        p.view_count,
                        p.anonymous,
                        p.created_at,

                        -- 이미지 리스트
                        COALESCE(
                            GROUP_CONCAT(DISTINCT pi.url ORDER BY pi.`index` SEPARATOR ','),
                            ''
                        ) AS images,

                        -- 좋아요한 유저 id 리스트
                        COALESCE(
                            GROUP_CONCAT(DISTINCT pl.user_id SEPARATOR ','),
                            ''
                        ) AS like_user_ids,

                        -- 댓글 개수
                        COUNT(DISTINCT pc.id) AS comment_count

                    FROM posts p
                    LEFT JOIN post_images pi 
                        ON p.post_id = pi.post_id AND pi.use_yn = TRUE
                    LEFT JOIN post_likes pl 
                        ON p.post_id = pl.post_id
                    LEFT JOIN post_comments pc
                        ON p.post_id = pc.post_id AND pc.deleted = FALSE

                    WHERE p.user_id = %s
                        AND p.deleted = FALSE

                    GROUP BY p.post_id
                    ORDER BY p.created_at DESC
                    """,
                    (user_id,),
                )

                rows = await cur.fetchall()
                return rows

    async def get_my_comments(self, user_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 
                        c.id,
                        c.post_id,
                        c.user_id,
                        c.content,
                        c.anonymous,
                        c.created_at,
                        COUNT(pcl.user_id) AS like_count
                    FROM post_comments c
                    LEFT JOIN post_comment_likes pcl
                        ON c.id = pcl.comment_id
                    WHERE c.user_id = %s
                        AND c.deleted = FALSE
                    GROUP BY c.id
                    ORDER BY c.created_at DESC
                    """,
                    (user_id,),
                )

                rows = await cur.fetchall()
                return rows

    async def block_comment(self, user_id: str, comment_id: int) -> bool:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()

                    # 1) 사용자 존재 체크
                    await cur.execute(
                        """
                        SELECT id FROM users 
                        WHERE id = %s AND leaved = FALSE
                        """,
                        (user_id,),
                    )
                    if not await cur.fetchone():
                        await conn.rollback()
                        return False

                    # 2) 댓글 존재 체크
                    await cur.execute(
                        """
                        SELECT id FROM post_comments
                        WHERE id = %s AND deleted = FALSE
                        """,
                        (comment_id,),
                    )
                    if not await cur.fetchone():
                        await conn.rollback()
                        return False

                    # 3) 차단 insert
                    await cur.execute(
                        """
                        INSERT INTO comment_block_list(block_user_id, blocked_comment_id)
                        VALUES(%s, %s)
                        """,
                        (user_id, comment_id),
                    )

                    await conn.commit()
                    return True

                except Exception as e:
                    await conn.rollback()
                    logger.error(f"댓글 차단 실패: {e}")
                    return False

    async def report_comment(
        self, report_comment_id: int, report_user_id: str, reason: str
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()

                    check_user = """
                        SELECT id FROM users WHERE id = %s AND leaved = %s
                    """
                    await cur.execute(check_user, (report_user_id, False))
                    user_row = await cur.fetchone()
                    if not user_row:
                        return False

                    check_comment = """
                        SELECT id, user_id FROM post_comments WHERE id = %s AND deleted = %s
                    """
                    await cur.execute(check_comment, (report_comment_id, False))
                    comment_row = await cur.fetchone()
                    if not comment_row:
                        return False

                    _, comment_user_id = comment_row

                    insert_query = """
                        INSERT INTO post_comment_reports(
                            report_comment_id,
                            reported_user_id,
                            report_user_id,
                            reason
                        )
                        VALUES(%s, %s, %s, %s)
                    """
                    await cur.execute(
                        insert_query,
                        (
                            report_comment_id,
                            comment_user_id,
                            report_user_id,
                            reason,
                        ),
                    )
                    await conn.commit()
                    await cur.close()
                    return True
                except Exception as e:
                    await conn.rollback()
                    logger.error(f"댓글 신고 실패: {e}")
                    return False

    async def fetch_post_user_id(self, post_id: str) -> Optional[str]:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT user_id
                    FROM posts
                    WHERE post_id = %s AND deleted = %s
                    """,
                    (post_id, False),
                )
                result = await cur.fetchone()
                if result:
                    return result[0]

    async def fetch_post_like_count(self, post_id: str) -> Optional[str]:
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM post_likes 
                    WHERE post_id = %s
                    """,
                    (post_id,),
                )
                result = await cur.fetchone()
                if result:
                    return result[0]
