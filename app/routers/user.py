from typing import List
from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, HTTPException, Form, UploadFile, File, status, Query
from fastapi import BackgroundTasks, Depends
from typing import Optional
from app.db.user import (
    UserCreateRequest,
    UserNicknameRequest,
    UserHashtagRequest,
    UserInfoRequest,
    UserFcmRequest,
    UserRelationRequest,
    UserPositionRequest,
    UserAlarmRequest,
    UserListRequest,
    UserLeaveRequest,
    UserBlockRequest,
    UserReportRequest,
    UserTalkStyleRequest,
    UserHealthCheckRequest,
    UserIntroductionRequest,
    UserBdsmRequest,
    UserCreditRequest,
    UserUnblockRequest,
    UserCreditSecretRequest,
    UserFavoriteRequest,
)
from app.services.user_service import UserService
from app.services.push_service import PushService
from app.repository.user_repository import UserRepository
from app.core.container import Container
from app.utils.token import get_user_id_from_token, JWTBearer
from app.db.db_connection import db
import uuid

oauth2_scheme = JWTBearer(auto_error=False)
# tags는 swagger에서 그룹핑할 때 사용
router = APIRouter(prefix="/v1/gik-backend", tags=["User"])


# user.py로 적어놓았으면 컨벤션을 user로 써야하지 않을까.
# [유저] 회원가입
@router.post("/user", status_code=status.HTTP_201_CREATED)
@inject
async def create_user_endpoint(
    service: UserService = Depends(Provide[Container.user_service]),
    user_form: UserCreateRequest = Depends(UserCreateRequest.create_form),
    profile_images: List[UploadFile] = File(default=[]),
    secret_images: Optional[List[UploadFile]] = File(default=[]),
):
    """
    유저 회원가입
    """
    result: bool = await service.create_user(
        user_form=user_form,
        profile_images=profile_images,
        secret_images=secret_images,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="이미 존재하는 유저입니다."
        )
    return {"message": "유저가 성공적으로 등록되었습니다."}


# [유저] 닉네임 중복 확인
@router.get("/user/check-nickname/{nickname}", status_code=status.HTTP_200_OK)
@inject
async def check_user_nickname(
    nickname: str, service: UserService = Depends(Provide[Container.user_service])
):
    """
    유저 닉네임 중복 확인
    nickname: 유저 닉네임
    """
    exist = await service.check_nickname(nickname)
    return {
        "success": True,
        "message": "중복된 닉네임입니다." if exist else "중복되지 않은 닉네임입니다.",
        "exist": exist,
    }


@router.get("/my-profile", status_code=status.HTTP_200_OK)
@inject
async def fetch_my_profile_by_token(
    token=Depends(oauth2_scheme),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 프로필 조회
    id: 유저 ID
    """
    id = await get_user_id_from_token(token)
    user = await service.fetch_my_profile(user_id=id)

    return {"success": True, "message": "내 정보 조회 성공", "user": user}


# TODO : 토큰으로 한번 검증 후에 만약 없다면 id로 검증.
# [유저] 내 정보 조회 (user_id로)
@router.get("/my-profile/{id}", status_code=status.HTTP_200_OK)
@inject
async def fetch_my_profile(
    id: str,
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 프로필 조회
    id: 유저 ID
    """
    user = await service.fetch_my_profile(user_id=id)

    return {"success": True, "message": "내 정보 조회 성공", "user": user}


# [유저] 내 정보 수정 (닉네임)
@router.patch("/my-profile/nickname", status_code=status.HTTP_200_OK)
@inject
async def update_user_nickname(
    user_nickname: UserNicknameRequest,
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 닉네임 수정
    id: 유저 ID
    nickname: 변경된 닉네임
    """
    result: bool = await service.update_user_nickname(
        user_nickname.id, user_nickname.nickname
    )
    if result == "duplicate":
        return {"success": False, "message": "이미 존재하는 닉네임입니다."}

    if result == "not_found":
        return {"success": False, "message": "나의 닉네임 변경 실패."}

    return {"success": True, "message": "나의 닉네임 변경 성공."}


# [유저] 내 정보 수정 (해시태그)
@router.patch("/my-profile/hashtag", status_code=status.HTTP_200_OK)
@inject
async def update_user_hashtag(
    user_hashtags: UserHashtagRequest,
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 해시태그 수정
    id: 유저 ID
    hashtags: 변경된 해시태그
    """
    result: bool = await service.update_user_hashtag(
        user_hashtags.id, user_hashtags.hashtags
    )
    if result is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="나의 해시태그 변경 실패."
        )
    return {"success": result, "message": "나의 해시태그 변경 성공."}


# [유저] 내 정보 수정 (기본정보)
@router.patch("/my-profile/info", status_code=status.HTTP_200_OK)
@inject
async def update_user_info(
    user_info: UserInfoRequest,
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 기본 정보 수정
    id: 유저 ID
    age: 나이
    height: 키
    weight: 몸무게
    country: 국가
    """
    result: bool = await service.update_user_info(
        user_info.id,
        user_info.age,
        user_info.height,
        user_info.weight,
        user_info.country,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="나의 기본정보 변경 실패."
        )
    return {"success": result, "message": "나의 기본정보 변경 성공."}


# [유저] 내 정보 수정 (fcm 코드)
@router.patch("/my-profile/fcm", status_code=status.HTTP_200_OK)
@inject
async def update_user_fcm(
    user_fcm: UserFcmRequest,
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 FCM 코드 수정
    id: 유저 ID
    fcm: 변경된 FCM 코드
    """
    result: bool = await service.update_user_fcm(user_fcm.id, user_fcm.fcm)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="나의 FCM 코드 변경 실패."
        )
    return {"success": result, "message": "나의 FCM 코드 변경 성공"}


# [유저] 내 정보 수정 (희망 관계)
@router.patch("/my-profile/relation", status_code=status.HTTP_200_OK)
@inject
async def update_user_relation(
    user_relation: UserRelationRequest,
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 희망 관계 수정
    id: 유저 ID
    relation: 변경된 희망 관계
    """
    result: bool = await service.update_user_relation(
        user_relation.id, user_relation.relation
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="나의 희망 관계 변경 실패."
        )
    return {"success": result, "message": "나의 희망 관계 변경 성공."}


# [유저] 내 정보 수정 (포지션)
@router.patch("/my-profile/position", status_code=status.HTTP_200_OK)
@inject
async def update_user_position(
    user_position: UserPositionRequest,
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 포지션 수정
    id: 유저 ID
    position: 변경된 포지션
    """
    result: bool = await service.update_user_position(
        user_position.id, user_position.position
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="나의 포지션 변경 실패."
        )
    return {"success": result, "message": "나의 포지션 변경 성공."}


# [유저] 내 소통 스타일 수정 (선택사항)
@router.post("/my-profile/talk-style", status_code=status.HTTP_200_OK)
@inject
async def update_user_talk_style(
    user_talk_style: UserTalkStyleRequest,
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 소통 스타일 수정
    id: 유저 ID
    talkStyle: 변경된 소통 스타일
    """
    result: bool = await service.update_user_talk_style(
        id=user_talk_style.id, talk_style=user_talk_style.talkStyle
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="나의 소통 스타일 변경 실패.",
        )
    return {"success": result, "message": "나의 소통 스타일 변경 성공."}


# [유저] 내 정보 수정 (알람)
@router.patch("/my-profile/alarm/{type}", status_code=status.HTTP_200_OK)
@inject
async def update_user_alarm(
    user_alarm: UserAlarmRequest,
    type: str,
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 알람 설정 수정
    id: 유저 ID
    type: 알람 종류 (markeing_agree, personal_chat, group_chat, post_comment, post_like, night_agree, profile_agree, secret_alarm_agree)
    value: 변경된 알람 설정 값 (True/False)
    """
    result: bool = await service.update_user_alarm(
        user_alarm.id, type, user_alarm.value
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="나의 알람 설정 변경 실패."
        )
    return {"success": result, "message": "나의 알람 설정 변경 성공."}


# [유저] 내 정보 수정 (자기소개)
@router.patch("/my-profile/self-introduction", status_code=status.HTTP_200_OK)
@inject
async def update_user_self_introduction(
    user_self_introduction: UserIntroductionRequest,
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 자기소개 변경
    user_self_introduction: 자기소개
    """
    result: bool = await service.update_user_self_introduction(
        id=user_self_introduction.id,
        user_self_introduction=user_self_introduction.selfIntroduction,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="나의 자기소개 변경 실패."
        )
    return {"success": result, "message": "나의 자기소개 변경 성공."}


# [유저] 내 정보 수정 (bdsm 타입)
@router.patch("/my-profile/bdsm-type", status_code=status.HTTP_200_OK)
@inject
async def update_user_bdsm_type(
    user_bdsm_type: UserBdsmRequest,
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 bdsm 타입 변경
    user_bdsm_type: bdsm 타입
    """
    result: bool = await service.update_user_bdsm_type(
        user_id=user_bdsm_type.id, bdsm_type=user_bdsm_type.bdsmType
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="나의 bdsm 타입 변경 실패."
        )
    return {"success": result, "message": "나의 bdsm 타입 변경 성공."}


# [유저] 상대 유저 상세정보 조회
@router.get("/user/{user_id}", status_code=status.HTTP_200_OK)
@inject
async def fetch_user_profile(
    user_id: str, service: UserService = Depends(Provide[Container.user_service])
):
    """
    상대 유저 프로필 조회
    user_id: 조회할 상대 유저 ID
    viewer_id: 조회한 주체
    """
    viewer_id = None
    user = await service.fetch_user_profile(user_id, viewer_id)

    return {"success": True, "message": "유저 정보 조회 성공", "user": user}


# [유저] 상대 유저의 차단 여부 확인 True/False로 체크
@router.get("/user/block/{target_user_id}", status_code=status.HTTP_200_OK)
@inject
async def check_user_block(
    target_user_id: str,
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    상대 유저의 차단 여부 확인
    token: 본인 엑세스 토큰
    user_id: 상대 유저 ID
    """
    user_id = await get_user_id_from_token(token)
    result = await service.check_user_block(
        user_id=user_id, target_user_id=target_user_id
    )
    return {
        "success": result,
        "message": "상대 유저의 차단 여부 확인 성공",
        "isBlocked": result,
    }


# [유저] 상대 유저 상세정보 조회(토큰, 푸시)
@router.get("/user-token/{user_id}", status_code=status.HTTP_200_OK)
@inject
async def fetch_user_profile_with_push(
    user_id: str,
    background_tasks: BackgroundTasks,
    token: str = Depends(oauth2_scheme),
    user_service: UserService = Depends(Provide[Container.user_service]),
    push_service: PushService = Depends(Provide[Container.push_service]),
):
    """
    상대 유저 프로필 조회
    user_id: 조회할 상대 유저 ID
    viewer_id: 본인 엑세스 토큰
    background_tasks: 백그라운드 task에 넣어 push 작업의 안정성 향상
    """

    # 1. push 작업 토큰을 사용해 api를 호출한 사용자의 id 가져오기
    viewer_id = await get_user_id_from_token(token)

    # 1-2. api 작업 - 조회할 상대방의 프로필 정보 가져오기
    target_profile = await user_service.fetch_user_profile(user_id, viewer_id)

    # user_id = 푸시 받을사람
    # viewer_id = 푸시 보내는 사람(프로필을 조회한 사람)
    await push_service.send_push_to_user(
        background_tasks=background_tasks,
        user_id=user_id,
        target_user_id=viewer_id,
        title_content="내 프로필을 보고 간 사람이 있어요 👀",
        body_content="누군가가 내 프로필을 보고 갔어요. 지금 접속해서 확인해 보세요!",
        data={"type": "profile", "viewerId": viewer_id},
        collapse_key=f"profile-view-{user_id}",
    )

    await user_service.insert_user_profile_view(user_id, viewer_id)

    return {
        "success": True,
        "message": "유저 정보 조회 성공",
        "user": target_profile,
    }


# [유저] 상대 유저 차단
@router.post("/user/block", status_code=status.HTTP_200_OK)
@inject
async def block_user(
    user_block: UserBlockRequest,
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    상대 유저 차단
    id: 유저 ID (본인)
    user_id: 차단할 상대 유저 ID
    """
    result = await service.block_user(user_block.id, user_block.userId)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="유저 차단 실패."
        )

    return {"success": result, "message": "유저 차단 성공."}


# [유저] 상대 유저 신고
@router.post("/user/report", status_code=status.HTTP_200_OK)
@inject
async def report_user(
    user_report: UserReportRequest,
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 신고
    chatId: 채팅방 ID (채팅방에서 신고했다면 존재)
    reportUserId: 신고하는 유저 ID
    reportedUserId: 신고당하는 유저 ID
    reason: 신고 사유
    """
    result = await service.report_user(
        user_report.chatId,
        user_report.reportUserId,
        user_report.reportedUserId,
        user_report.reason,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="유저 신고 실패."
        )

    return {"success": result, "message": "유저 신고 성공."}


# [유저] 유저 목록으로 조회
@router.post("/users/list", status_code=status.HTTP_200_OK)
@inject
async def fetch_user_list(
    user_id_list: UserListRequest,
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 목록으로 조회
    user_id: 조회할 유저 ID 목록
    """
    user_id = await get_user_id_from_token(token)
    users = await service.fetch_user_list(user_id, user_id_list.userIdList)
    return {"success": True, "message": "유저 목록 조회 성공", "users": users}


# [유저] 유저 ID 목록 조회 (탈퇴하지 않은 유저 전체) / 희망하는 관계, 소통 스타일을 쿼리 파라미터로 받아서 필터
@router.get("/users/id_list", status_code=status.HTTP_200_OK)
@inject
async def fetch_user_id_list(
    token: str = Depends(oauth2_scheme),
    position: str = None,
    relation: str = None,
    bdsmType: str = None,
    talkStyle: str = None,
    age: str = None,
    secret: bool = None,
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 ID 목록 조회
    """
    user_id = None
    if token:
        user_id = await get_user_id_from_token(token)
    user_ids = await service.fetch_user_id_list(
        user_id=user_id,
        position=position,
        relation=relation,
        bdsm_type=bdsmType,
        talk_style=talkStyle,
        age=age,
        secret=secret,
    )
    return {"success": True, "message": "유저 ID 목록 조회 성공", "userIds": user_ids}


# [유저] 유저 ID 목록 조회, 근처 유저 순서대로 ORDER BY
@router.get("/users/id_list/near", status_code=status.HTTP_200_OK)
@inject
async def fetch_near_user_id_list(
    token: str = Depends(oauth2_scheme),
    age: str = None,
    position: str = None,
    relation: str = None,
    bdsmType: str = None,
    talkStyle: str = None,
    secret: bool = None,
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 ID 목록 조회, 근처 유저 순서대로 ORDER BY
    """
    # get_user_id_from_token을 쓰는 이유는, verify_token이 Optional[str] 이기 때문에 사용할 수 없음.
    # get_user_id_from_token이 있는 이유는 str을 반환하기 때문.
    user_id = await get_user_id_from_token(token)
    user_ids = await service.fetch_near_user_id_list(
        user_id,
        age=age,
        position=position,
        relation=relation,
        bdsm_type=bdsmType,
        talk_style=talkStyle,
        secret=secret,
    )
    return {
        "success": True,
        "message": "근처 유저 ID 목록 조회 성공",
        "userIds": user_ids,
    }


# [유저] 유저 FCM 목록 조회 (탈퇴하지 않은 유저 전체) 유저id리스트 보내주면
@router.post("/users/fcm_list", status_code=status.HTTP_200_OK)
@inject
async def fetch_user_fcm_list(
    user_id_list: UserListRequest,
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 FCM 목록 조회
    """

    fcm_list = await service.fetch_user_fcm_list(user_id_list.userIdList)

    return {"success": True, "message": "유저 FCM 목록 조회 성공", "fcmList": fcm_list}


# [유저] 회원 탈퇴 (leaved 탈퇴)
@router.post("/leave", status_code=status.HTTP_200_OK)
@inject
async def leave_user(
    user_leave: UserLeaveRequest,
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 탈퇴
    """

    result = await service.leave_user(user_leave.id, user_leave.reason)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="유저 탈퇴 실패."
        )
    return {"success": result, "message": "유저 탈퇴 성공."}


@router.patch("/user/health/{user_id}", status_code=status.HTTP_200_OK)
@inject
async def user_health_check(
    user_id: str,
    user_health: Optional[UserHealthCheckRequest] = None,
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 실시간 정보를 찍기 위한 API
    """

    result = await service.user_health_check(
        user_id,
        user_latitude=user_health.userLatitude if user_health else None,
        user_longitude=user_health.userLongitude if user_health else None,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유저 실시간 정보 업데이트 실패.",
        )
    return {"success": result, "message": "유저 실시간 정보 업데이트 성공."}


@router.patch("/user/images", status_code=status.HTTP_200_OK)
@inject
async def update_user_images(
    user_id: str = Form(...),
    image_index: Optional[List[str]] = Form(default=[]),
    images: Optional[List[UploadFile]] = File(default=None),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 프로필 사진 수정
    user_id: 이미지를 사용한 사용자의 id
    image_index: 수정할 이미지 인덱스
    image_label: 이미지 사용처
        - user_profile: 유저 프로필 사진
    """
    image_url_list = await service.update_user_images(user_id, image_index, images)

    if not image_url_list:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 수정 실패.",
        )

    return {
        "success": True,
        "message": "이미지 수정 성공",
        "image_urls": image_url_list,
    }


@router.get("/push/list", status_code=status.HTTP_200_OK)
@inject
async def fetch_user_push_list(
    push_type: Optional[str] = Query(None),
    page: int = Query(...),
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저가 받은 푸시 목록 조회
    page: 페이지 번호 (1부터 시작)
    push_type: 푸시 타입(없으면 전체, userAction, announcement)
    """
    user_id = await get_user_id_from_token(token)
    push_list = await service.fetch_user_push_list(
        push_type=push_type, page=page, user_id=user_id
    )

    return {
        "success": True,
        "message": "유저 푸시 목록 조회 성공",
        "pushList": push_list,
    }


@router.patch("/user/push/receive", status_code=status.HTTP_200_OK)
@inject
async def receive_user_push(
    push_id: str = Query(...),
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저의 푸시 수신, db의 delivery_state를 OPENED로 변경
    push_id: 푸시 ID
    """
    # 토큰에서 유저 아이디 추출,
    user_id = await get_user_id_from_token(token)
    result = await service.receive_user_push(push_id=push_id, user_id=user_id)

    if result is False:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="유저 푸시 수신 처리 실패.",
        )

    return {"success": result, "message": "유저 푸시 수신 처리 성공"}


@router.patch("/user/push/all-receive", status_code=status.HTTP_200_OK)
@inject
async def receive_all_user_push(
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저의 모든 푸시 수신, db의 delivery_state를 OPENED로 변경
    """
    # 토큰에서 유저 아이디 추출,
    user_id = await get_user_id_from_token(token)
    result = await service.receive_all_user_push(user_id=user_id)

    if result is False:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="유저 모든 푸시 수신 처리 실패.",
        )

    return {"success": result, "message": "유저 모든 푸시 수신 처리 성공"}


@router.get("/user/profile/viewed", status_code=status.HTTP_200_OK)
@inject
async def fetch_user_profile_view(
    page: int = Query(...),
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저를 보고간 사람 조회
    """

    user_id = await get_user_id_from_token(token)
    result = await service.fetch_user_profile_view(page=page, user_id=user_id)

    return {
        "success": True,
        "message": "유저를 보고간 사람 조회 성공",
        "viewList": [view.model_dump() for view in result],
    }


# [시크릿] 상대 유저의 시크릿 앨범 열람 푸시 전송
@router.post("/secret/push", status_code=status.HTTP_200_OK)
@inject
async def fetch_user_secret_images(
    background_tasks: BackgroundTasks,
    token: str = Depends(oauth2_scheme),
    target_user_id: str = Query(...),
    user_service: UserService = Depends(Provide[Container.user_service]),
    push_service: PushService = Depends(Provide[Container.push_service]),
):
    """
    유저 시크릿 앨범 열람시 푸시
    user_id: token에서 추출, 시크릿 앨범 열람 요청 주체
    target_user_id: 시크릿 앨범 열람 요청 대상 유저 ID
    """
    # api를 호출한 사용자의 id
    user_id = await get_user_id_from_token(token)

    # 내 시크릿 앨범에 사진이 없다면
    is_image = await user_service.fetch_my_secret_images(user_id)
    if is_image is None:
        await user_service.insert_user_secret_images_view(user_id, target_user_id)
        return {"success": False, "message": "내 시크릿 앨범에 사진이 없습니다."}

    await push_service.send_push_to_user(
        background_tasks=background_tasks,
        user_id=user_id,
        target_user_id=target_user_id,
        title_content="내 시크릿 앨범을 보고 간 사람이 있어요 💋",
        body_content="누군가가 내 시크릿 앨범💋을 보고 갔어요. 지금 접속해서 확인해 보세요!",
        data={"type": "secret", "requestId": user_id},
        collapse_key=f"secret-view-{user_id}",
    )

    await user_service.insert_user_secret_images_view(user_id, target_user_id)

    return {"success": True, "message": "시크릿 앨범 열람 성공"}


@router.get("/secret-list", status_code=status.HTTP_200_OK)
@inject
async def fetch_user_secret_list(
    page: int = Query(...),
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    내 시크릿 앨범을 조회한 사람들 조회
    user_id: token에서 추출
    """
    user_id = await get_user_id_from_token(token)
    secret_list = await service.fetch_user_secret_list(page=page, user_id=user_id)
    return {
        "success": True,
        "message": "내 시크릿 앨범을 조회한 사람들 조회 성공",
        "secretList": secret_list,
    }


@router.post("/secret/credit", status_code=status.HTTP_200_OK)
@inject
async def insert_user_credit_secret_list(
    credit_secret: UserCreditSecretRequest,
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    내가 결제한 시크릿 앨범 추가
    user_id: token에서 추출
    secret_user_id: 결제한 시크릿 앨범 유저 ID
    """
    user_id = await get_user_id_from_token(token)
    result = await service.insert_user_credit_secret_list(
        user_id=user_id, secret_user_id=credit_secret.userId
    )
    if result is False:
        return {
            "success": False,
            "message": "유저의 시크릿 앨범이 존재하지 않습니다.",
        }
    return {"success": result, "message": "내가 결제한 시크릿 앨범 추가 성공"}


# TODO: 내가 결제한 시크릿 앨범 목록 조회.
@router.get("/secret/credit-list", status_code=status.HTTP_200_OK)
@inject
async def fetch_user_credit_secret_view(
    page: int = Query(...),
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    내가 결제한 시크릿 앨범 목록 조회
    user_id: token에서 추출
    """
    user_id = await get_user_id_from_token(token)
    credit_secret_list = await service.fetch_user_credit_secret_view(
        page=page, user_id=user_id
    )
    return {
        "success": True,
        "message": "내가 결제한 시크릿 앨범 목록 조회 성공",
        "creditSecretList": credit_secret_list,
    }


# [시크릿] 상대 유저에게 시크릿 앨범 열람 수락
@router.patch("/secret/images/accept", status_code=status.HTTP_200_OK)
@inject
async def accept_user_secret_images(
    background_tasks: BackgroundTasks,
    token: str = Depends(oauth2_scheme),
    target_user_id: str = Query(...),
    user_service: UserService = Depends(Provide[Container.user_service]),
    push_service: PushService = Depends(Provide[Container.push_service]),
):
    """
    유저 시크릿 앨범 열람 수락
    user_id: token에서 추출, 시크릿 앨범 열람 수락 주체
    target_user_id: 시크릿 앨범 열람 수락 대상 유저 ID
    """
    user_id = await get_user_id_from_token(token)

    # api를 호출한 사용자의 닉네임 가져오기
    user_nickname = await user_service.fetch_user_nickname(user_id)

    await push_service.send_push_to_user(
        background_tasks=background_tasks,
        user_id=user_id,
        target_user_id=target_user_id,
        title_content="시크릿 앨범 열람 수락",
        body_content=f"{user_nickname}님이 회원님의 시크릿 앨범 열람 요청을 수락했습니다.",
        data={"type": "secret", "requestId": user_id},
        collapse_key=f"secret-view-{user_id}",
    )
    await user_service.accept_user_secret_images(user_id, target_user_id)

    return {"success": True, "message": "시크릿 앨범 열람 수락 성공"}


# [시크릿] 상대 유저에게 시크릿 앨범 열람 거절
@router.patch("/secret/images/reject", status_code=status.HTTP_200_OK)
@inject
async def reject_user_secret_images(
    token: str = Depends(oauth2_scheme),
    target_user_id: str = Query(...),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 시크릿 앨범 열람 거절
    user_id: token에서 추출, 시크릿 앨범 열람 거절 주체
    target_user_id: 시크릿 앨범 열람 거절 대상 유저 ID
    """
    user_id = await get_user_id_from_token(token)
    await service.reject_user_secret_images(user_id, target_user_id)
    return {"success": True, "message": "시크릿 앨범 열람 거절 성공"}


# [시크릿] 내 시크릿 앨범 요청 취소
@router.patch("/secret/images/cancel", status_code=status.HTTP_200_OK)
@inject
async def cancel_my_secret_request(
    token: str = Depends(oauth2_scheme),
    target_user_id: str = Query(...),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 시크릿 앨범 요청 취소
    user_id: token에서 추출, 시크릿 앨범 요청 취소 주체
    target_user_id: 시크릿 앨범 요청 취소 대상 유저 ID
    """
    user_id = await get_user_id_from_token(token)
    await service.cancel_my_secret_request(user_id, target_user_id)
    return {"success": True, "message": "시크릿 앨범 요청 취소 성공"}


# [시크릿] 내가 요청한 시크릿 앨범 열람건 조회
@router.get("/secret/images/requests", status_code=status.HTTP_200_OK)
@inject
async def fetch_my_secret_request(
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    내가 상대에게 요청한 시크릿 앨범 요청건 조회
    user_id: token에서 추출, 유저가 상대에게 요청한 시크릿 앨범건 주체
    """
    user_id = await get_user_id_from_token(token)
    requests = await service.fetch_my_secret_requests(user_id)
    return {
        "success": True,
        "message": "내가 요청한 시크릿 앨범건 조회 성공",
        "requests": requests,
    }


# [시크릿] 나에게 온 시크릿 앨범 요청건 조회
@router.get("/secret/images/accepts", status_code=status.HTTP_200_OK)
@inject
async def fetch_opponent_secret_request(
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    나에게 온 상대의 시크릿 앨범 요청건 조회
    user_id: token에서 추출, 유저에게 온 상대방들의 시크릿 앨범 요청건 주체
    """
    user_id = await get_user_id_from_token(token)
    accepts = await service.fetch_opponent_secret_requests(user_id)
    return {
        "success": True,
        "message": "나에게 온 시크릿 앨범 열람 요청건 조회 성공",
        "accepts": accepts,
    }


# [시크릿] 내 시크릿 앨범 허용 취소
@router.patch("/secret/images/cancel-accept", status_code=status.HTTP_200_OK)
@inject
async def cancel_accept_my_secret_request(
    token: str = Depends(oauth2_scheme),
    target_user_id: str = Query(...),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 시크릿 앨범 허용 취소
    user_id: token에서 추출, 시크릿 앨범 허용 취소 주체
    target_user_id: 시크릿 앨범 허용 취소 대상 유저 ID
    """
    user_id = await get_user_id_from_token(token)
    await service.cancel_accept_my_secret_request(user_id, target_user_id)
    return {"success": True, "message": "시크릿 앨범 허용 취소 성공"}


# [시크릿] 요청 수락된 시크릿 앨범 조회
@router.get("/secret/images", status_code=status.HTTP_200_OK)
@inject
async def fetch_accepted_secret_images(
    token: str = Depends(oauth2_scheme),
    target_user_id: str = Query(...),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    요청 수락된 시크릿 앨범 조회
    user_id: token에서 추출, 시크릿 앨범 조회 주체
    target_user_id: 시크릿 앨범 조회 대상 유저 ID
    """
    user_id = await get_user_id_from_token(token)
    image_urls = await service.fetch_accepted_secret_images(user_id, target_user_id)
    if image_urls is None:
        return {
            "success": False,
            "message": "시크릿 앨범이 없거나, 열람 권한이 없습니다.",
            "image_urls": [],
        }
    return {
        "success": True,
        "message": "시크릿 앨범 조회 성공",
        "image_urls": image_urls,
    }


@router.post("/user/credit/give", status_code=status.HTTP_200_OK)
@inject
async def give_user_credit(
    user_credit_type: UserCreditRequest,
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    사용자에게 재화 리워드 제공
    user_id: token에서 추출, 크레딧 지급 주체
    user_credit_type:
        - type: 크레딧 지급 사유, history_reward (프로필 조회 시 광고 시청 리워드)
    """
    user_id = await get_user_id_from_token(token)
    result = await service.give_user_credit(user_id, user_credit_type.type)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="광고 시청 크레딧 지급 실패.",
        )

    return {
        "success": True,
        "message": f"{result} 고래 코인 지급 성공.",
        "amount": result,
    }


@router.post("/user/credit/consume", status_code=status.HTTP_200_OK)
@inject
async def consume_user_credit(
    user_credit_type: UserCreditRequest,
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    사용자의 재화 소모
    user_id: token에서 추출, 크레딧 소모 주체
    user_credit:
        - type: 크레딧 지급 사유, history_view (프로필 조회 시 크레딧 소모), secret_view(시크릿 앨범 열람시 크레딧 소모)
    """
    user_id = await get_user_id_from_token(token)
    result = await service.consume_user_credit(user_id, user_credit_type.type)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="크레딧 소모 실패."
        )
    return {
        "success": True,
        "message": f"{result} 고래 코인 소모 성공.",
        "amount": result,
    }


@router.post("/user/credit/{user_id}", status_code=status.HTTP_200_OK)
@inject
async def add_user_credit_profile_view(
    user_id: str,
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    내가 결제해서 본 사용자 추가
    viewer_id: token에서 추출, 크레딧 소모해서 조회하는 사용자
    user_id: 조회한 사용자 ID
    """
    viewer_id = await get_user_id_from_token(token)
    result = await service.add_user_credit_profile_view(
        viewer_id=viewer_id,
        viewed_id=user_id,
    )
    return {
        "success": result,
        "message": "내가 결제해서 본 사용자 리스트 업데이트 성공.",
    }


@router.get("/user/credit/profile", status_code=status.HTTP_200_OK)
@inject
async def fetch_user_credit_profile_view(
    page: int = Query(...),
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    내가 결제해서 본 사용자 리스트
    user_id: token에서 추출, 크레딧 소모 주체
    page: 페이지 번호 (1부터 시작)
    """
    user_id = await get_user_id_from_token(token)
    result = await service.fetch_user_credit_profile_view(user_id, page)
    return {
        "success": True,
        "message": "내가 결제해서 본 사용자 리스트 조회 성공",
        "viewList": result,
    }


@router.get("/users/block", status_code=status.HTTP_200_OK)
@inject
async def fetch_user_block_list(
    page: int = Query(...),
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    내가 차단한 유저 리스트
    user_id: token에서 추출, 차단한 유저 리스트 조회 주체
    """
    user_id = await get_user_id_from_token(token)
    result = await service.fetch_user_block_list(page=page, user_id=user_id)
    return {
        "success": True,
        "message": "내가 차단한 유저 리스트 조회 성공",
        "blockList": result,
    }


@router.patch("/users/block", status_code=status.HTTP_200_OK)
@inject
async def unblock_user(
    user_block: UserUnblockRequest,
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    상대 유저 차단 해제
    user_id: token에서 추출, 차단 해제 주체
    target_user_id: 차단 해제할 상대 유저 ID
    """
    user_id = await get_user_id_from_token(token)
    result = await service.unblock_user(user_id, user_block.userId)
    return {
        "success": result,
        "message": "유저 차단 해제 성공.",
    }


# TOBE: 아직 구체화가 더 필요.
@router.post("/users/poke/{target_user_id}", status_code=status.HTTP_200_OK)
@inject
async def poke_user(
    target_user_id: str,
    background_tasks: BackgroundTasks,
    token: str = Depends(oauth2_scheme),
    user_service: UserService = Depends(Provide[Container.user_service]),
    push_service: PushService = Depends(Provide[Container.push_service]),
):
    """
    유저 찔러보기
    pocker_id: token에서 추출, 찔러보기 주체
    target_user_id: 찔러볼 대상 유저 ID
    """
    pocker_id = await get_user_id_from_token(token)

    # api를 호출한 사용자의 닉네임 가져오기
    user_nickname = await user_service.fetch_user_nickname(pocker_id)

    await push_service.send_push_to_user(
        background_tasks=background_tasks,
        user_id=pocker_id,
        target_user_id=target_user_id,
        title_content="누군가가 회원님을 찔렀어요! 👀",
        body_content=f"{user_nickname}님이 회원님을 찔렀어요! 지금 접속해서 확인해 보세요!",
        data={"type": "poke", "requestId": pocker_id},
        collapse_key=f"poke-{pocker_id}",
    )

    await user_service.poke_user(pocker_id, target_user_id)
    return {"success": True, "message": "유저 찔러보기 성공"}


# TOBE: 아직 구체화가 더 필요.
@router.get("/users/poke-list", status_code=status.HTTP_200_OK)
@inject
async def fetch_my_poke_list(
    page: int = Query(...),
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    나를 찔러본 유저 리스트
    user_id: token에서 추출, 찔러본 유저 리스트 조회 주체
    """
    user_id = await get_user_id_from_token(token)
    result = await service.fetch_my_poke_list(page=page, user_id=user_id)
    return {
        "success": True,
        "message": "나를 찔러본 유저 리스트 조회 성공",
        "pokeList": result,
    }


@router.post("/users/favorite", status_code=status.HTTP_200_OK)
@inject
async def favorite_user(
    target_user_id: UserFavoriteRequest,
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    유저 즐겨찾기 추가
    user_id: token에서 추출, 즐겨찾기 주체
    target_user_id: 즐겨찾기할 대상 유저 ID
    """
    user_id = await get_user_id_from_token(token)
    result = await service.favorite_user(user_id, target_user_id.userId)
    if result:
        return {
            "success": True,
            "message": "유저 즐겨찾기 해제 성공.",
        }
    else:
        return {
            "success": True,
            "message": "유저 즐겨찾기 성공.",
        }


# 내가 결제해서 해제한 프로필/시크릿 앨범 갯수
@router.get("/user/unlock/count", status_code=status.HTTP_200_OK)
@inject
async def fetch_user_unlock_count(
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(Provide[Container.user_service]),
):
    """
    내가 결제해서 본 프로필 갯수
    user_id: token에서 추출, 블라인드 프로필을 결제한 주체
    """
    user_id = await get_user_id_from_token(token)
    count = await service.fetch_user_unlock_count(user_id)
    return {
        "success": True,
        "message": "내가 결제해서 본 프로필 갯수 조회 성공",
        "profileCount": count.profileCount,
        "secretCount": count.secretCount,
    }
