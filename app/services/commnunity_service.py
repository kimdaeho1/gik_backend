# app/services/community_service.py
from app.db.community import FullPostMigrationRequest
from app.db.db_connection import db

class CommunityService:
    def __init__(self):
        self.db = db

    async def migrate_full_post(self, data: FullPostMigrationRequest):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()

                    # 1. posts
                    await cur.execute("""
                        INSERT INTO posts (
                            post_id, user_id, title, content, view_count,
                            anonymous, deleted, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        data.post_id, data.user_id, data.title, data.content,
                        data.view_count, data.anonymous, False, data.created_at, data.created_at
                    ))

                    # 2. post_images
                    for image in data.images:
                        await cur.execute("""
                            INSERT INTO post_images (post_id, user_id, `index`, url, use_yn)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            data.post_id, data.user_id, image.index, image.url, True
                        ))

                    # 3. post_likes
                    for uid in data.like_user_ids:
                        await cur.execute("""
                            INSERT INTO post_likes (post_id, user_id, created_at)
                            VALUES (%s, %s, %s)
                        """, (data.post_id, uid, data.created_at))

                    # 4. post_comments
                    for comment in data.comments:
                        await cur.execute("""
                            INSERT INTO post_comments (
                                post_id, user_id, content, anonymous, deleted, created_at, updated_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            data.post_id, comment.user_id, comment.content,
                            comment.anonymous, False, comment.created_at, comment.created_at
                        ))

                    # 5. post_reports
                    for report in data.post_reports:
                        await cur.execute("""
                            INSERT INTO post_reports (
                                report_user_id, reported_user_id, reported_post_id, reason, created_at
                            ) VALUES (%s, %s, %s, %s, %s)
                        """, (
                            report.report_user_id, data.user_id, data.post_id,
                            report.reason, report.created_at
                        ))

                    # 6. post_comment_reports
                    for cr in data.comment_reports:
                        await cur.execute("""
                            INSERT INTO post_comment_reports (
                                report_user_id, reported_user_id, reported_comment_id, reason, created_at
                            ) VALUES (%s, %s, %s, %s, %s)
                        """, (
                            cr.report_user_id, data.user_id, cr.comment_id,
                            cr.reason, cr.created_at
                        ))

                    await conn.commit()

                except Exception as e:
                    await conn.rollback()
                    raise e

