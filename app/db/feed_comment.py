from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class CreateFeedCommentRequest(BaseModel):
    content: str


class UpdateFeedCommentRequest(BaseModel):
    content: str


class ReportFeedCommentRequest(BaseModel):
    reportedUserId: str
    reason: str


class FeedCommentResponse(BaseModel):
    commentId: int
    userId: str
    content: str
    createdAt: datetime
