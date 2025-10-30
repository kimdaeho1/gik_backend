from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from fastapi import Form


class CreateFeedRequest(BaseModel):
    content: Optional[str] = None
    status: bool
    secretStatus: bool
    price: Optional[int] = 10

    @classmethod
    def create_feed_request(
        cls,
        content: Optional[str] = Form(None),
        status: bool = Form(...),
        secretStatus: bool = Form(...),
        price: Optional[int] = Form(10),
    ):
        return cls(
            content=content,
            status=status,
            secretStatus=secretStatus,
            price=price,
        )


# imageUrl = 수정하지 않아도 되는 사진 url 리스트
class UpdateFeedRequest(BaseModel):
    content: Optional[str] = None
    imageUrl: Optional[List[str]] = None
    status: bool
    secretStatus: bool
    price: Optional[int] = 10

    @classmethod
    def update_feed_request(
        cls,
        content: Optional[str] = Form(None),
        imageUrl: Optional[List[str]] = Form(None),
        status: bool = Form(...),
        secretStatus: bool = Form(...),
        price: Optional[int] = Form(10),
    ):
        return cls(
            content=content,
            imageUrl=imageUrl,
            status=status,
            secretStatus=secretStatus,
            price=price,
        )


# reportedUserId = 신고당한 유저 아이디
class ReportFeedRequest(BaseModel):
    reportedUserId: str
    reason: str


# fetch_my_profile 할때 피드 차단 리스트를 들고올지, 여기서 들고올지?
# 피드 리스트를 들고올때, List[FeedDetailResponse] 형태로 들고옴, 내 피드 리스트를 불러올때도 마찬가지.
class FeedDetailResponse(BaseModel):
    feedId: str
    userId: str
    content: Optional[str]
    images: Optional[List[str]]
    status: bool
    secretStatus: bool
    likeCount: int
    commentCount: int
    isLiked: bool
    isPurchased: bool
    price: int
    createdAt: datetime
