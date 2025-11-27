from fastapi import HTTPException, status
from app.db.db_connection import db
from typing import List, Optional
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class BizRepository:
    def __init__(self, db):
        self.db = db

    async def get_biz_account(self, biz_id: str):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT *
                    FROM biz_account
                    WHERE biz_id = %s
                    """,
                    (biz_id,),
                )
                biz = await cur.fetchone()
                return biz

    async def update_biz_tokens(
        self,
        biz_id: str,
        access_token: str,
        refresh_token: str,
    ):
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE biz_account
                    SET access_token = %s, refresh_token = %s
                    WHERE biz_id = %s
                    """,
                    (access_token, refresh_token, biz_id),
                )

    async def login_biz_account(
        self,
        biz_id: str,
        biz_password: str,
    ): ...
