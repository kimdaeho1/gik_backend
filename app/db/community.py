from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class PostRequest(BaseModel):
    userId: str
    title: str
    content: str
    images: Optional[List[str]]


class PostEditRequest(BaseModel):
    title: str
    content: str
    images: Optional[List[str]]
    

class PostDeleteRequest(BaseModel):
    userId: str
    postId: str


class PostBlockRequest(BaseModel):
    userId: str
    blockPostId: str


class PostCommentRequest(BaseModel):
    postId: str
    userId: str
    content: str


class PostCommentEditRequest(BaseModel):
    userId: str
    postId: int
    content: str
    

class PostListResponse(BaseModel):
    id: str
    userId: str
    title: str
    content: str
    images: List[str]
    viewCount: int
    likeUserIds: List[str]
    commentCount: int
    anonymous: bool
    createdAt: str

class PostLikeRequest(BaseModel):
    userId: str
    postId: str
    

class CommentResponse(BaseModel):
    id: int
    userId: str
    content: str
    

class PostDetailResponse(BaseModel):
    id: str
    userId: str
    title: str
    content: str
    viewCount: int
    likeCount: int
    images: List[str]
    comments: List[CommentResponse]
    likeUserIds: List[str]
    anonymous: bool
    createdAt: str


class PostReportRequest(BaseModel):
    reportPostId: str
    reportUserId: str
    reason: str


class PostCommentListResponse(BaseModel):
    comments: List[CommentResponse]


class CommentLikeRequest(BaseModel):
    userId: str
    commentId: int


class CommentEditRequest(BaseModel):
    userId: str
    commentId: int
    content: str


class CommentDeleteRequest(BaseModel):
    userId: str
    commentId: int
