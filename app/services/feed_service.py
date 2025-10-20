from fastapi import HTTPException, status
from datetime import datetime
from app.utils.s3_upload import upload_file_to_s3, generate_filename
from app.db.feed import (
    FeedDetailResponse,
)

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class FeedService:
    def __init__(self, feed_repository):
        self.feed_repository = feed_repository

    async def create_feed(
        self,
        token,
        create_feed_request,
        feed_images,
    ): ...

    async def update_feed(): ...

    async def delete_feed(): ...

    async def get_feed(): ...

    async def report_feed(): ...

    async def block_feed(): ...

    async def like_feed(): ...

    async def unlike_feed(): ...

    async def get_my_feed_list(): ...

    async def get_feed_list(): ...
