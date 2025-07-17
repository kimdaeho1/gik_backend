from pydantic import BaseModel, Field
from typing import List, Dict

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
    nickname: str
    age: int
    height: int
    weight: int
    relation: str
    position: str
    hashtags: Hashtags
    profileImages: List[str]


class UserDetailResponse(BaseModel):
    id: str
    nickname: str
    profileImages: List[str]
    relation: str
    position: str
    country: str
    age: int
    height: int
    weight: int
    hashtags: Hashtags


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
