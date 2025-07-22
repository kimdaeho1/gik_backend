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
    

# TODO 삭제 


# postid를 어떻게 할건지? 생성할때 현재는 post_id가 없는 상태.
class PostLikeRequest(BaseModel):
    postId: int
    userId: str
    likePostId: int
    

class PostBlockRequest(BaseModel):
    postId: int
    userId: str
    blockPostId: int


class PostCommentRequest(BaseModel):
    postId: int
    userId: str
    content: str


class PostCommentEditRequest(BaseModel):
    userId: str
    postId: int
    content: str
    

class PostDetailResponse(BaseModel):
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
