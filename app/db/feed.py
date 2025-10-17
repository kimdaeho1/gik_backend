from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class CreateFeedRequest(BaseModel):
    content: Optional[str] = None
    status: bool
    secretStatus: bool


# imageUrl = 수정하지 않아도 되는 사진 url 리스트
class UpdateFeedRequest(BaseModel):
    content: Optional[str] = None
    imageUrl: Optional[List[str]] = None
    status: bool
    secretStatus: bool


# reportedUserId = 신고당한 유저 아이디
class ReportFeedRequest(BaseModel):
    reportedUserId: str
    reason: str


# blockedUserId = 차단할 유저 아이디
class BlockFeedRequest(BaseModel):
    blockedUserId: str


# fetch_my_profile 할때 피드 차단 리스트를 들고올지, 여기서 들고올지?
# 피드 리스트를 들고올때, List[FeedDetailResponse] 형태로 들고옴, 내 피드 리스트를 불러올때도 마찬가지.
class FeedDetailResponse(BaseModel):
    userId: str
    content: Optional[str]
    images: Optional[List[str]]
    status: bool
    secretStatus: bool
    likeCount: int
    createdAt: datetime
