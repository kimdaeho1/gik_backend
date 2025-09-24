from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class Hashtags(BaseModel):
    bodyType: List[str]
    hobbies: List[str]
    outfitStyle: List[str]
    personality: List[str]


class User(BaseModel):
    id: str
    fcm: str
    email: str
    name: str
    phone: str
    birthday: str
    provider: str
    sns: str
    nickname: str
    profileImages: List[str]
    age: int
    height: int
    weight: int
    country: str
    position: str
    relation: str
    hashtags: Hashtags
    personalChatAlarm: bool
    groupChatAlarm: bool
    postCommentAlarm: bool
    postLikeAlarm: bool
    serviceAgree: bool
    personalAgree: bool
    marketingAgree: bool
    nightAgree: bool
    leave: bool


class UserProfileResponse(BaseModel):
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
    pushRead: bool
    profileRead: bool
    banned: bool
    unBannedDate: Optional[datetime]
    blockUserList: Optional[List[str]]
    blockPostList: Optional[List[str]]
    blockCommentList: Optional[List[str]]
    lastConnectedAt: datetime
    latitude: Optional[float]
    longitude: Optional[float]


class UserDetailResponse(BaseModel):
    id: str
    fcm: str
    nickname: str
    birthday: str
    profileImages: List[str]
    relation: str
    position: str
    country: str
    age: int
    height: int
    weight: int
    hashtags: Hashtags
    selfIntroduction: Optional[str]
    bdsmType: Optional[str]
    talkStyle: Optional[str]
    secretYn: bool
    secretImages: Optional[List[str]]
    leaved: bool
    blockUserList: Optional[List[str]]
    personalChatAlarm: bool
    groupChatAlarm: bool
    postCommentAlarm: bool
    postLikeAlarm: bool
    lastConnectedAt: datetime
    latitude: Optional[float]
    longitude: Optional[float]
    isBlocked: bool


class UserListResponse(BaseModel):
    id: str
    fcm: str
    nickname: str
    birthday: str
    profileImages: List[str]
    relation: str
    position: str
    country: str
    age: int
    height: int
    weight: int
    hashtags: Hashtags
    selfIntroduction: Optional[str]
    bdsmType: Optional[str]
    talkStyle: Optional[str]
    secretYn: bool
    secretImages: List[str]
    leaved: bool
    blockUserList: Optional[List[str]]
    personalChatAlarm: bool
    groupChatAlarm: bool
    postCommentAlarm: bool
    postLikeAlarm: bool
    lastConnectedAt: datetime
    latitude: Optional[float]
    longitude: Optional[float]


class UserNicknameRequest(BaseModel):
    id: str
    nickname: str


class UserHashtagRequest(BaseModel):
    id: str
    hashtags: Hashtags


class UserInfoRequest(BaseModel):
    id: str
    age: int
    height: int
    weight: int
    country: str


class UserFcmRequest(BaseModel):
    id: str
    fcm: str


class UserRelationRequest(BaseModel):
    id: str
    relation: str


class UserPositionRequest(BaseModel):
    id: str
    position: str


class UserAlarmRequest(BaseModel):
    id: str
    value: bool


class UserIntroductionRequest(BaseModel):
    id: str
    selfIntroduction: str


class UserBdsmRequest(BaseModel):
    id: str
    bdsmType: str


class UserListRequest(BaseModel):
    userIdList: List[str]


class UserLeaveRequest(BaseModel):
    id: str
    reason: str


class UserBlockRequest(BaseModel):
    id: str
    userId: str


class UserReportRequest(BaseModel):
    chatId: Optional[str] = None
    reportUserId: str
    reportedUserId: str
    reason: str


class UserImageDeleteRequest(BaseModel):
    userId: str
    imageIndex: int


class UserTalkStyleRequest(BaseModel):
    id: str
    talkStyle: str


class UserHealthCheckRequest(BaseModel):
    userLatitude: Optional[float] = None
    userLongitude: Optional[float] = None


class UserCreditRequest(BaseModel):
    type: str
