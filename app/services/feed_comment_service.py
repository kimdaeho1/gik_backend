from fastapi import HTTPException, status
from datetime import datetime
from app.utils.s3_upload import upload_file_to_s3, generate_filename
from app.db.feed import (
    FeedDetailResponse,
)

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class FeedCommentService:
    def __init__(self, feed_comment_repository):
        self.feed_comment_repository = feed_comment_repository

    async def create_feed_comment(): ...

    async def update_feed_comment(): ...

    async def delete_feed_comment(): ...

    async def get_feed_comment_list(): ...

    async def block_feed_comment(): ...

    async def report_feed_comment(): ...
