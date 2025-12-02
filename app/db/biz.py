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


class BizDetailRow(BaseModel):
    id: str
    biz_id: str
    store_type: str
    store_name: str
    tags: str
    address: str
    business_hours: str
    phone: str
    manager_phone: str
    latitude: Optional[float]
    longitude: Optional[float]
    fcm: Optional[str]
    credit: int
    marketing_agree: bool
    night_agree: bool
    personal_chat_alarm_agree: bool
    group_chat_alarm_agree: bool
    post_comment_alarm_agree: bool
    post_like_alarm_agree: bool
    profile_alarm_agree: bool
    feed_like_alarm_agree: bool
    feed_comment_alarm_agree: bool
    image_urls: Optional[str]
    block_user_list: Optional[str]
    favorite_user_list: Optional[str]
    push_read: bool
    profile_read: bool
    has_secret_feed: bool


class BizProfileResponse(BaseModel):
    id: str
    bizId: str
    storeType: str
    storeName: str
    tags: str
    address: str
    businessHours: str
    phoneNumber: str
    managerPhone: str
    latitude: Optional[float]
    longitude: Optional[float]
    fcm: Optional[str]
    credit: int
    marketingAlarm: bool
    nightAlarm: bool
    personalChatAlarm: bool
    groupChatAlarm: bool
    postCommentAlarm: bool
    postLikeAlarm: bool
    profileAlarm: bool
    feedLikeAlarm: bool
    feedCommentAlarm: bool
    profileImage: Optional[List[str]]
    blockUserList: Optional[List[str]]
    favoriteUserList: Optional[List[str]]
    pushRead: bool
    profileRead: bool
    hasSecretFeed: bool
