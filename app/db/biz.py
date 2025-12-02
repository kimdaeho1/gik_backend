from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from fastapi import Form


class BizAccountRequest(BaseModel):
    bizId: str
    bizPassword: str


class BizCouponRequest(BaseModel):
    title: str
    content: str
    startDate: Optional[str] = None
    expiredDate: Optional[str] = None
    amount: Optional[int] = None


class BizUpdateRequest(BaseModel):
    couponId: int
    title: str
    content: str
    amount: int
    startDate: str
    expiredDate: str


class Hashtags(BaseModel):
    bodyType: List[str]
    hobbies: List[str]
    outfitStyle: List[str]
    personality: List[str]


class BizProfileResponse(BaseModel):
    id: str
    nickname: str
    birthday: str
    age: int
    height: int
    weight: int
    sns: str
    relation: str
    provider: str
    position: str
    country: str
    hashtags: Hashtags
    selfIntroduction: Optional[str]
    bdsmType: Optional[str]
    talkStyle: Optional[str]
    profileImages: List[str]
    secretYn: bool
    credit: int
    todayAdCount: int
    secretImages: List[str]
    marketingAlarm: bool
    nightAlarm: bool
    personalChatAlarm: bool
    groupChatAlarm: bool
    postCommentAlarm: bool
    postLikeAlarm: bool
    profileAlarm: bool
    secretAlarm: bool
    feedLikeAlarm: bool
    feedCommentAlarm: bool
    pushRead: bool
    profileRead: bool
    banned: bool
    unBannedDate: Optional[datetime]
    blockUserList: Optional[List[str]]
    blockPostList: Optional[List[str]]
    blockCommentList: Optional[List[str]]
    favoriteUserList: Optional[List[str]]
    lastConnectedAt: datetime
    latitude: Optional[float]
    longitude: Optional[float]
    hasSecretFeed: bool
