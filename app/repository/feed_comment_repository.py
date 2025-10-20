from fastapi import UploadFile, HTTPException
from app.db.image import UserSecretResponse
from app.db.db_connection import db
from typing import List, Optional
from app.utils.logging_config import get_logger
from app.utils.firebase_init import init_firebase_admin
from firebase_admin import auth
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class FeedCommentRepository:
    def __init__(self):
        pass
