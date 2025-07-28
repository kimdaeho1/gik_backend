from typing import List
from fastapi import APIRouter, HTTPException, Form, UploadFile, File, status
from app.db.user import Hashtags, UserProfileResponse, UserDetailResponse, UserNicknameRequest, UserHashtagRequest, UserInfoRequest, UserFcmRequest, UserRelationRequest, UserPositionRequest, UserAlarmRequest, UserListRequest, UserLeaveRequest, UserBlockRequest, UserReportRequest
from app.services.user_service import UserService


router = APIRouter()
user_service = UserService()

# TODO: device_os 필요할듯
# [유저] 회원가입
@router.post("/v1/gik-backend/user", status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    id: str = Form(...),
    fcm: str = Form(...),
    email: str = Form(...),
    name: str = Form(...),
    phone: str = Form(...),
    birthday: str = Form(...),
    provider: str = Form(...),
    sns: str = Form(...),
    nickname: str = Form(...),
    profile_images: List[UploadFile] = File(default=[]),
    age: int = Form(...),
    height: int = Form(...),
    weight: int = Form(...),
    country: str = Form(...),
    position: str = Form(...),
    relation: str = Form(...),
    hashtags: str = Form(...),
    personal_chat_alarm: bool = Form(...),
    group_chat_alarm: bool = Form(...),
    post_comment_alarm: bool = Form(...),
    post_like_alarm: bool = Form(...),
    service_agree: bool = Form(...),
    personal_agree: bool = Form(...),
    marketing_agree: bool = Form(...),
    night_agree: bool = Form(...),
    leave: bool = Form(...)
):
    """
    유저 회원가입
    """
    hashtags_obj = Hashtags.parse_raw(hashtags)

    result: bool = await user_service.create_user(
        id=id,
        fcm=fcm,
        email=email,
        name=name,
        phone=phone,
        birthday=birthday,
        provider=provider,
        sns=sns,
        nickname=nickname,
        profile_images=profile_images,
        age=age,
        height=height,
        weight=weight,
        country=country,
        position=position,
        relation=relation,
        hashtags=hashtags_obj,
        personal_chat_alarm=personal_chat_alarm,
        group_chat_alarm=group_chat_alarm,
        post_comment_alarm=post_comment_alarm,
        post_like_alarm=post_like_alarm,
        service_agree=service_agree,
        personal_agree=personal_agree,
        marketing_agree=marketing_agree,
        night_agree=night_agree,
        leave=leave
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 존재하는 유저입니다."
        )
    return {"message": "유저가 성공적으로 등록되었습니다."}



# [유저] 닉네임 중복 확인
@router.get("/v1/gik-backend/user/check-nickname/{nickname}", status_code=status.HTTP_200_OK) 
async def check_user_nickname(
    nickname: str
):
    """
    유저 닉네임 중복 확인
    nickname: 유저 닉네임
    """
    exist = await user_service.check_nickname(nickname)
    return {
        "success": True,
        "message": "중복된 닉네임입니다." if exist else "중복되지 않은 닉네임입니다.",
        "exist": exist
    }


# [유저] 내 정보 조회 (user_id로)
@router.get("/v1/gik-backend/my-profile/{id}", status_code=status.HTTP_200_OK)
async def fetch_my_profile(
    id: str
):
    """
    유저 프로필 조회
    id: 유저 ID
    """
    user = await user_service.fetch_my_profile(id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="내 정보 없음."
        )
    return {
        "success": True,
        "message": "내 정보 조회 성공",
        "user": user
    }


# [유저] 내 정보 수정 (닉네임)
@router.patch("/v1/gik-backend/my-profile/nickname", status_code=status.HTTP_200_OK)
async def update_user_nickname(
    user_nickname: UserNicknameRequest
):
    """
    유저 닉네임 수정
    id: 유저 ID
    nickname: 변경된 닉네임
    """
    result: bool = await user_service.update_user_nickname(
        user_nickname.id, user_nickname.nickname
        )
    if result == "duplicate":
        return {
            "success": False,
            "message": "이미 존재하는 닉네임입니다."
        }
    
    if result == "not_found":
        return {
            "success": False,
            "message": "나의 닉네임 변경 실패."
        }
    
    return {"success": True, "message": "나의 닉네임 변경 성공."}


# [유저] 내 정보 수정 (해시태그)
@router.patch("/v1/gik-backend/my-profile/hashtag", status_code=status.HTTP_200_OK)
async def update_user_hashtag(
    user_hashtags: UserHashtagRequest
):
    """
    유저 해시태그 수정
    id: 유저 ID
    hashtags: 변경된 해시태그
    """
    result: bool = await user_service.update_user_hashtag(
        user_hashtags.id, user_hashtags.hashtags
    )
    if result is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="나의 해시태그 변경 실패."
        )
    return {"success": result, "message": "나의 해시태그 변경 성공."}


# [유저] 내 정보 수정 (기본정보)
@router.patch("/v1/gik-backend/my-profile/info", status_code=status.HTTP_200_OK)
async def update_user_info(
    user_info: UserInfoRequest
):
    """
    유저 기본 정보 수정
    id: 유저 ID
    age: 나이
    height: 키
    weight: 몸무게
    country: 국가
    """
    result: bool = await user_service.update_user_info(
        user_info.id,
        user_info.age,
        user_info.height,
        user_info.weight,
        user_info.country
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="나의 기본정보 변경 실패."
        )
    return {"success": result, "message": "나의 기본정보 변경 성공."}


# [유저] 내 정보 수정 (fcm 코드)
@router.patch("/v1/gik-backend/my-profile/fcm", status_code=status.HTTP_200_OK)
async def update_user_fcm(
    user_fcm: UserFcmRequest
):
    """
    유저 FCM 코드 수정
    id: 유저 ID
    fcm: 변경된 FCM 코드
    """
    result: bool = await user_service.update_user_fcm(
        user_fcm.id,
        user_fcm.fcm
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="나의 FCM 코드 변경 실패."
        )
    return {"success": result, "message": "나의 FCM 코드 변경 성공"}


# [유저] 내 정보 수정 (희망 관계)
@router.patch("/v1/gik-backend/my-profile/relation", status_code=status.HTTP_200_OK)
async def update_user_relation(
    user_relation: UserRelationRequest
):
    """
    유저 희망 관계 수정
    id: 유저 ID
    relation: 변경된 희망 관계
    """
    result: bool = await user_service.update_user_relation(
        user_relation.id,
        user_relation.relation
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="나의 희망 관계 변경 실패."
        )
    return {"success": result, "message": "나의 희망 관계 변경 성공."}



# [유저] 내 정보 수정 (포지션)
@router.patch("/v1/gik-backend/my-profile/position", status_code=status.HTTP_200_OK)
async def update_user_position(
    user_position: UserPositionRequest
):
    """
    유저 포지션 수정
    id: 유저 ID
    position: 변경된 포지션
    """
    result: bool = await user_service.update_user_position(
        user_position.id,
        user_position.position
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="나의 포지션 변경 실패."
        )
    return {"success": result, "message": "나의 포지션 변경 성공."}
    

# [유저] 내 정보 수정 (알람)
@router.patch("/v1/gik-backend/my-profile/alarm/{type}", status_code=status.HTTP_200_OK)
async def update_user_alarm(
    user_alarm: UserAlarmRequest,
    type: str
):
    """
    유저 알람 설정 수정
    id: 유저 ID
    type: 알람 종류 (markeing_agree, personal_chat, group_chat, post_comment, post_like, night_agree)
    value: 변경된 알람 설정 값 (True/False)
    """
    result: bool = await user_service.update_user_alarm(
        user_alarm.id,
        type,
        user_alarm.value
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="나의 알람 설정 변경 실패."
        )
    return {"success": result, "message": "나의 알람 설정 변경 성공."}


# [유저] 상대 유저 상세정보 조회
@router.get("/v1/gik-backend/user/{user_id}", status_code=status.HTTP_200_OK)
async def fetch_user_profile(
    user_id: str
):
    """
    상대 유저 프로필 조회
    id: 유저 ID (본인)
    user_id: 조회할 상대 유저 ID
    """
    user = await user_service.fetch_user_profile(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="유저 정보 조회 실패."
        )
    
    return {
        "success": True,
        "message": "유저 정보 조회 성공",
        "user": user
    }
    

# [유저] 상대 유저 차단
@router.post("/v1/gik-backend/user/block", status_code=status.HTTP_200_OK)
async def block_user(
    user_block: UserBlockRequest
):
    """
    상대 유저 차단
    id: 유저 ID (본인)
    user_id: 차단할 상대 유저 ID
    """
    result = await user_service.block_user(
        user_block.id,
        user_block.userId
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유저 차단 실패."
        )
    
    return {"success": result, "message": "유저 차단 성공."}


# [유저] 상대 유저 신고
@router.post("/v1/gik-backend/user/report", status_code=status.HTTP_200_OK)
async def report_user(
    user_report: UserReportRequest
):
    """
    유저 신고
    chatId: 채팅방 ID (채팅방에서 신고했다면 존재)
    reportUserId: 신고하는 유저 ID
    reportedUserId: 신고당하는 유저 ID
    reason: 신고 사유
    """
    result = await user_service.report_user(
        user_report.chatId,
        user_report.reportUserId,
        user_report.reportedUserId,
        user_report.reason
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유저 신고 실패."
        )
    
    return {"success": result, "message": "유저 신고 성공."}


# [유저] 유저 목록으로 조회
@router.post("/v1/gik-backend/users/list", status_code=status.HTTP_200_OK)
async def fetch_user_list(
    user_id_list: UserListRequest
):
    """
    유저 목록으로 조회
    user_id: 조회할 유저 ID 목록
    """
    
    users = await user_service.fetch_user_list(user_id_list.userIdList)
    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="유저 목록 조회 실패."
        )
    
    return {
        "success": True,
        "message": "유저 목록 조회 성공",
        "users": users
    }


# [유저] 유저 ID 목록 조회 (탈퇴하지 않은 유저 전체)
@router.get("/v1/gik-backend/users/id_list", status_code=status.HTTP_200_OK)
async def fetch_user_id_list(
):
    """
    유저 ID 목록 조회
    """
    user_ids = await user_service.fetch_user_id_list()
    if not user_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="유저 ID 목록 조회 실패."
        )
    
    return {
        "success": True,
        "message": "유저 ID 목록 조회 성공",
        "userIds": user_ids
    }


# [유저] 유저 FCM 목록 조회 (탈퇴하지 않은 유저 전체) 유저id리스트 보내주면
@router.post("/v1/gik-backend/users/fcm_list", status_code=status.HTTP_200_OK)
async def fetch_user_fcm_list(
    user_id_list: UserListRequest
):
    """
    유저 FCM 목록 조회
    """
    
    fcm_list = await user_service.fetch_user_fcm_list(user_id_list.userIdList)
    if not fcm_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="유저 FCM 목록 조회 실패."
        )
    
    return {
        "success": True,
        "message": "유저 FCM 목록 조회 성공",
        "fcmList": fcm_list
    }


# [유저] 회원 탈퇴 (leaved 탈퇴)
@router.post("/v1/gik-backend/leave", status_code=status.HTTP_200_OK)
async def leave_user(
    user_leave: UserLeaveRequest
):
    """
    유저 탈퇴
    """
    
    result = await user_service.leave_user(
        user_leave.id,
        user_leave.reason
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유저 탈퇴 실패."
        )
    return {"success": result, "message": "유저 탈퇴 성공."}
