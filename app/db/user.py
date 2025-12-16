from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from fastapi import Form
from typing import Any, Dict


class Hashtags(BaseModel):
    bodyType: List[str]
    hobbies: List[str]
    outfitStyle: List[str]
    personality: List[str]


# name, phone, birthday
class UserCreateRequest(BaseModel):
    id: str
    fcm: str
    email: str
    name: str
    phone: str
    birthday: str
    provider: str
    sns: str
    nickname: str
    age: int
    height: int
    weight: int
    country: str
    position: str
    relation: str
    hashtags: str
    self_introduction: Optional[str] = None
    bdsm_type: Optional[str] = None
    personal_chat_alarm: bool
    group_chat_alarm: bool
    post_comment_alarm: bool
    post_like_alarm: bool
    service_agree: bool
    personal_agree: bool
    marketing_agree: bool
    night_agree: bool
    leave: bool
    test: Optional[str] = ""
    auth: bool = True

    @classmethod
    def create_form(
        cls,
        id: str = Form(...),
        fcm: str = Form(...),
        email: str = Form(...),
        name: str = Form(...),
        phone: str = Form(...),
        birthday: str = Form(...),
        provider: str = Form(...),
        sns: str = Form(...),
        nickname: str = Form(...),
        age: int = Form(...),
        height: int = Form(...),
        weight: int = Form(...),
        country: str = Form(...),
        position: str = Form(...),
        relation: str = Form(...),
        hashtags: str = Form(...),
        self_introduction: Optional[str] = Form(default=None),
        bdsm_type: Optional[str] = Form(default=None),
        personal_chat_alarm: bool = Form(...),
        group_chat_alarm: bool = Form(...),
        post_comment_alarm: bool = Form(...),
        post_like_alarm: bool = Form(...),
        service_agree: bool = Form(...),
        personal_agree: bool = Form(...),
        marketing_agree: bool = Form(...),
        night_agree: bool = Form(...),
        leave: bool = Form(...),
        test: Optional[str] = Form(default=""),
        auth: bool = Form(default=True),
    ) -> "UserCreateRequest":
        return cls(
            id=id,
            fcm=fcm,
            email=email,
            name=name,
            phone=phone,
            birthday=birthday,
            provider=provider,
            sns=sns,
            nickname=nickname,
            age=age,
            height=height,
            weight=weight,
            country=country,
            position=position,
            relation=relation,
            hashtags=hashtags,
            self_introduction=self_introduction,
            bdsm_type=bdsm_type,
            personal_chat_alarm=personal_chat_alarm,
            group_chat_alarm=group_chat_alarm,
            post_comment_alarm=post_comment_alarm,
            post_like_alarm=post_like_alarm,
            service_agree=service_agree,
            personal_agree=personal_agree,
            marketing_agree=marketing_agree,
            night_agree=night_agree,
            leave=leave,
            test=test,
            auth=auth,
        )


# name, phone, birthday, provider
class NoAuthUserCreateRequest(BaseModel):
    id: str
    fcm: str
    email: str
    sns: str
    nickname: str
    age: int
    height: int
    weight: int
    country: str
    position: str
    relation: str
    hashtags: str
    self_introduction: Optional[str] = None
    bdsm_type: Optional[str] = None
    personal_chat_alarm: bool
    group_chat_alarm: bool
    post_comment_alarm: bool
    post_like_alarm: bool
    service_agree: bool
    personal_agree: bool
    marketing_agree: bool
    night_agree: bool
    leave: bool
    test: Optional[str] = ""
    auth: bool = False

    @classmethod
    def create_form(
        cls,
        id: str = Form(...),
        fcm: str = Form(...),
        email: str = Form(...),
        sns: str = Form(...),
        nickname: str = Form(...),
        age: int = Form(...),
        height: int = Form(...),
        weight: int = Form(...),
        country: str = Form(...),
        position: str = Form(...),
        relation: str = Form(...),
        hashtags: str = Form(...),
        selfIntroduction: Optional[str] = Form(default=None),
        bdsmType: Optional[str] = Form(default=None),
        personalChatAlarm: bool = Form(...),
        groupChatAlarm: bool = Form(...),
        postCommentAlarm: bool = Form(...),
        postLikeAlarm: bool = Form(...),
        serviceAgree: bool = Form(...),
        personalAgree: bool = Form(...),
        marketingAgree: bool = Form(...),
        nightAgree: bool = Form(...),
        leave: bool = Form(...),
        test: Optional[str] = Form(default=""),
        auth: bool = Form(default=False),
    ):
        return cls(
            id=id,
            fcm=fcm,
            email=email,
            sns=sns,
            nickname=nickname,
            age=age,
            height=height,
            weight=weight,
            country=country,
            position=position,
            relation=relation,
            hashtags=hashtags,
            self_introduction=selfIntroduction,
            bdsm_type=bdsmType,
            personal_chat_alarm=personalChatAlarm,
            group_chat_alarm=groupChatAlarm,
            post_comment_alarm=postCommentAlarm,
            post_like_alarm=postLikeAlarm,
            service_agree=serviceAgree,
            personal_agree=personalAgree,
            marketing_agree=marketingAgree,
            night_agree=nightAgree,
            leave=leave,
            test=test,
            auth=auth,
        )


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
    secretAlarm: bool
    feedLikeAlarm: bool
    feedCommentAlarm: bool
    followAlarm: bool
    pushRead: bool
    profileRead: bool
    banned: bool
    unBannedDate: Optional[datetime]
    auth: bool
    blockUserList: Optional[List[str]]
    blockPostList: Optional[List[str]]
    blockCommentList: Optional[List[str]]
    favoriteUserList: Optional[List[str]]
    lastConnectedAt: datetime
    latitude: Optional[float]
    longitude: Optional[float]
    hasSecretFeed: bool
    followerCount: int
    followingCount: int
    followingList: Optional[List[str]]
    useCouponList: Optional[List[int]]


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
    auth: bool
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
    todayViewCount: int
    totalViewCount: int
    followerCount: int
    followingCount: int


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
    auth: bool
    secretImages: List[str]
    leaved: bool
    blockUserList: Optional[List[str]]
    isBlocked: bool
    personalChatAlarm: bool
    groupChatAlarm: bool
    postCommentAlarm: bool
    postLikeAlarm: bool
    lastConnectedAt: datetime
    latitude: Optional[float]
    longitude: Optional[float]
    followerCount: int
    followingCount: int


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


class UserUnblockRequest(BaseModel):
    userId: str


class UserCreditSecretRequest(BaseModel):
    userId: str


class UserFavoriteRequest(BaseModel):
    userId: str


class UserProfileRow(BaseModel):
    id: str
    nickname: str
    birthday: str
    age: int
    height: int
    weight: int
    sns: str
    relation: str
    position: str
    country: str
    hashtags: str
    self_introduction: Optional[str]
    bdsm_type: Optional[str]
    talk_style: Optional[str]
    secret_yn: bool
    credit: int
    provider: str
    marketing_agree: bool
    night_agree: bool
    personal_chat_alarm_agree: bool
    group_chat_alarm_agree: bool
    post_comment_alarm_agree: bool
    post_like_alarm_agree: bool
    profile_alarm_agree: bool
    secret_alarm_agree: bool
    feed_like_alarm_agree: bool
    feed_comment_alarm_agree: bool
    banned: bool
    unbanned_dt: Optional[datetime]
    last_connected_at: datetime
    latitude: Optional[float]
    longitude: Optional[float]


class UserDetailRow(BaseModel):
    id: str
    fcm: Optional[str]
    nickname: str
    birthday: str
    age: int
    height: int
    weight: int
    sns: str
    relation: str
    position: str
    country: str
    hashtags: str
    self_introduction: Optional[str]
    bdsm_type: Optional[str]
    talk_style: Optional[str]
    secret_yn: bool
    credit: int
    provider: str
    marketing_agree: bool
    night_agree: bool
    personal_chat_alarm_agree: bool
    group_chat_alarm_agree: bool
    post_comment_alarm_agree: bool
    post_like_alarm_agree: bool
    profile_alarm_agree: bool
    secret_alarm_agree: bool
    feed_like_alarm_agree: bool
    feed_comment_alarm_agree: bool
    follow_alarm_agree: bool
    banned: bool
    unbanned_dt: Optional[datetime]
    auth_yn: bool
    last_connected_at: datetime
    latitude: Optional[float]
    longitude: Optional[float]
    profileImages: Optional[str]
    secretImages: Optional[str]
    blockUserList: Optional[str]
    favoriteUserList: Optional[str]
    pushRead: bool
    profileRead: bool
    todayAdCount: int
    hasSecretFeed: bool
    followerCount: int
    followingCount: int
    followingList: Optional[str]
    useCouponList: Optional[str]


class UserDetailViewRow(BaseModel):
    id: str
    fcm: Optional[str]
    nickname: str
    birthday: str
    age: int
    height: int
    weight: int
    sns: str
    relation: str
    position: str
    country: str
    hashtags: str
    self_introduction: Optional[str]
    bdsm_type: Optional[str]
    talk_style: Optional[str]
    secret_yn: bool
    auth_yn: bool
    leaved: bool
    last_connected_at: datetime
    latitude: Optional[float]
    longitude: Optional[float]
    personal_chat_alarm_agree: bool
    group_chat_alarm_agree: bool
    post_comment_alarm_agree: bool
    post_like_alarm_agree: bool
    profileImages: Optional[str]
    secretImages: Optional[str]
    blockUserList: Optional[str]
    followerCount: int
    followingCount: int


class UserListRow(BaseModel):
    id: str
    fcm: Optional[str]
    nickname: str
    birthday: str
    age: int
    height: int
    weight: int
    relation: str
    position: str
    country: str
    hashtags: str
    self_introduction: Optional[str]
    bdsm_type: Optional[str]
    leaved: bool
    talk_style: Optional[str]
    secret_yn: bool
    auth_yn: bool
    personal_chat_alarm_agree: bool
    group_chat_alarm_agree: bool
    post_comment_alarm_agree: bool
    post_like_alarm_agree: bool
    last_connected_at: datetime
    latitude: Optional[float]
    longitude: Optional[float]
    profileImages: Optional[List[str]] = []
    secretImages: Optional[List[str]] = []
    blockUserList: Optional[List[str]] = []
    isBlocked: Optional[bool] = False
    followerCount: int
    followingCount: int


class ProfileViewRow(BaseModel):
    id: str
    viewedAt: datetime
    viewCount: int
    todayViewCount: int


class ViewCountRow(BaseModel):
    viewerId: str
    viewedAt: datetime
    viewCount: int
    todayViewCount: int


class CountRow(BaseModel):
    profileCount: int
    secretCount: int


class UserCreditHistoryResponse(BaseModel):
    amount: int
    title: str
    description: str
    createdAt: datetime


class UserCreditProfileRequest(BaseModel):
    type: Optional[str]


class BizReviewRequest(BaseModel):
    bizId: str
    rating: int
    content: str

    @classmethod
    def create_form(
        cls,
        bizId: str = Form(...),
        rating: int = Form(...),
        content: str = Form(...),
    ) -> "BizReviewRequest":
        return cls(
            bizId=bizId,
            rating=rating,
            content=content,
        )


class BizReviewUpdateRequest(BaseModel):
    reviewId: str
    rating: int
    content: str
    images: Optional[List[str]] = None

    @classmethod
    def create_form(
        cls,
        reviewId: str = Form(...),
        rating: int = Form(...),
        content: str = Form(...),
        images: Optional[List[str]] = Form(default=None),
    ) -> "BizReviewUpdateRequest":
        return cls(
            reviewId=reviewId,
            rating=rating,
            content=content,
            images=images,
        )


class BizDetailResponse(BaseModel):
    id: str
    bizId: str
    storeType: str
    storeName: str
    email: Optional[str]
    tags: str
    address: str
    businessHours: str
    phone: str
    managerPhone: str
    latitude: Optional[float]
    longitude: Optional[float]


class BizReviewRow(BaseModel):
    id: int
    user_id: str
    nickname: str
    biz_id: str
    content: str
    images: List[str] = []
    rating: int
    created_at: datetime
    answer_content: Optional[str] = None
    answer_created_at: Optional[datetime] = None


class BizReviewResponse(BaseModel):
    id: int
    userId: str
    userNickname: str
    bizId: str
    content: str
    images: List[str] = []
    rating: int
    answer: Optional[Dict[str, Any]] = None
    createdAt: datetime


class BizReviewUpdateRequest(BaseModel):
    content: str
    rating: int
    image: Optional[List[str]]

    @classmethod
    def create_form(
        cls,
        content: str = Form(...),
        rating: int = Form(...),
        image: Optional[List[str]] = Form(default=None),
    ) -> "BizReviewUpdateRequest":
        return cls(
            content=content,
            rating=rating,
            image=image,
        )


class UserFollowRequest(BaseModel):
    userId: str


class ReviewReportRequest(BaseModel):
    reason: str


class VerifyUserRequest(BaseModel):
    name: str
    phone: str
    birthday: str
    provider: str
