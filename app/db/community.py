# app/models/community.py

from pydantic import BaseModel
from typing import List
from datetime import datetime

class PostImage(BaseModel):
    url: str
    index: int

class PostComment(BaseModel):
    comment_id: str  # Firebase comment 문서 ID (필요시 저장)
    user_id: str
    content: str
    anonymous: bool
    created_at: datetime

class PostReport(BaseModel):
    report_user_id: str
    reason: str
    created_at: datetime

class CommentReport(BaseModel):
    comment_id: str
    report_user_id: str
    reason: str
    created_at: datetime

class FullPostMigrationRequest(BaseModel):
    post_id: str
    user_id: str
    title: str
    content: str
    anonymous: bool
    created_at: datetime
    images: List[PostImage] = []
    like_user_ids: List[str] = []
    comments: List[PostComment] = []
    post_reports: List[PostReport] = []
    comment_reports: List[CommentReport] = []