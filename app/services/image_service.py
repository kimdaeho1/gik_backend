from fastapi import UploadFile, HTTPException
from datetime import datetime
from app.utils.s3_upload import upload_file_to_s3, CLOUDFRONT_URL
from app.db.db_connection import db
from app.db.image import UserSecretResponse
from typing import List, Optional


class ImageService:
    def __init__(self):
        self.db = db

    async def upload_user_secret_images(
        self,
        user_id: str,
        image: List[UploadFile],
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT 1 FROM users WHERE id = %s AND leaved = FALSE", (user_id,)
                )
                result = await cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404, detail="존재하지 않은 유저입니다"
                    )

                try:
                    await cur.execute(
                        """
                        SELECT COALESCE(MAX(`index`), -1)
                        FROM user_secret_images
                        WHERE user_id = %s AND use_yn = TRUE
                        """,
                        (user_id,),
                    )
                    max_index = (await cur.fetchone())[0] or -1

                    image_url_list = []
                    for idx, file in enumerate(image, start=max_index + 1):
                        now = datetime.now().strftime("%Y%m%d_%H%M%S%f")[:-3]
                        extension = (
                            file.filename.split(".")[-1].lower()
                            if file.filename
                            else "jpg"
                        )
                        filename = f"{now}.{extension}"
                        s3_key = f"user_secret_profile/{user_id}/"

                        file.file.seek(0)
                        if not upload_file_to_s3(file.file, s3_key, filename):
                            # 업로드 실패 시 전체 롤백
                            await conn.rollback()
                            raise HTTPException(
                                status_code=500,
                                detail=f"Failed to upload image {file.filename} to S3",
                            )

                        image_url = f"{CLOUDFRONT_URL}/{s3_key}{filename}"
                        await cur.execute(
                            """
                            INSERT INTO user_secret_images (user_id, `index`, url, use_yn)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (user_id, idx, image_url, True),
                        )
                        image_url_list.append(image_url)

                    await cur.execute(
                        "UPDATE users SET secret_yn = TRUE, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                        (user_id,),
                    )

                    await conn.commit()
                    return image_url_list

                except Exception as e:
                    # 어떤 오류든 발생하면 롤백
                    await conn.rollback()
                    raise e

    async def update_secret_images(
        self,
        user_id: str,
        image_index: Optional[List[str]] = None,
        image: Optional[List[UploadFile]] = None,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT 1 FROM users WHERE id = %s AND leaved = FALSE", (user_id,)
                )
                result = await cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="User not found")

                await cur.execute(
                    "SELECT url FROM user_secret_images WHERE user_id = %s AND use_yn = TRUE ORDER BY `index`",
                    (user_id,),
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
                remove_images = [
                    url for url in origin_image_urls if url not in image_index
                ]

                if remove_images:
                    for url in remove_images:
                        await cur.execute(
                            """
                            UPDATE user_secret_images
                            SET use_yn = FALSE
                            WHERE user_id = %s AND url = %s
                            """,
                            (user_id, url),
                        )

                for idx, url in enumerate(keep_images):
                    await cur.execute(
                        """
                        UPDATE user_secret_images
                        SET `index` = %s
                        WHERE user_id = %s AND url = %s
                        """,
                        (idx, user_id, url),
                    )

                start_index = len(keep_images)
                if image:
                    for idx, file in enumerate(image):
                        now = datetime.now().strftime("%Y%m%d_%H%M%S%f")[:-3]
                        extension = file.filename.split(".")[-1] or "jpg"
                        filename = f"{now}.{extension}"
                        s3_key = f"user_secret_profile/{user_id}/"

                        file.file.seek(0)
                        if not upload_file_to_s3(file.file, s3_key, filename):
                            raise HTTPException(
                                status_code=500,
                                detail=f"Failed to upload image {file.filename} to S3",
                            )

                        image_url = f"{CLOUDFRONT_URL}/{s3_key}{filename}"
                        await cur.execute(
                            """
                            INSERT INTO user_secret_images (user_id, `index`, url, use_yn)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (user_id, start_index + idx, image_url, True),
                        )

                    await cur.execute(
                        "UPDATE users SET secret_yn = TRUE WHERE id = %s", (user_id,)
                    )

                image_query = """
                    SELECT url 
                    FROM user_secret_images
                    WHERE user_id = %s AND use_yn = TRUE
                    ORDER BY `index`
                """
                await cur.execute(image_query, (user_id,))
                rows = await cur.fetchall()
                image_url_list = [row[0] for row in rows]
                if not image_url_list:
                    await cur.execute(
                        "UPDATE users SET secret_yn = FALSE WHERE id = %s", (user_id,)
                    )
                    await conn.commit()
                    return []

                # updated_at 필드 업데이트
                await cur.execute(
                    "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (user_id,),
                )

                await conn.commit()
                return image_url_list
