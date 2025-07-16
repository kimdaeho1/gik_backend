from typing import List
from fastapi import APIRouter, HTTPException, Form, UploadFile, status
from app.db.user import User
from app.services.user_service import UserService

router = APIRouter()
user_service = UserService()

# [유저] 회원가입
@router.post("/v1/gik-backend/user", status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    user: User,
):
    """
    유저 회원가입
    User: 유저 회원가입 정보
    """
    result: bool = await user_service.create_user(user)

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
    result: bool = await user_service.check_nickname(nickname)
    if result:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 존재하는 닉네임입니다."
        )
    return {"message": "사용 가능한 닉네임입니다."}


# [유저] 내 정보 조회
# @router.get("/v1/gik-backend/my-profile", status_code=status.HTTP_200_OK)


# # [유저] 내 정보 수정 (닉네임)
# @router.patch("/v1/gik-backend/my-profile/nickname", status_code=status.HTTP_200_OK)


# # [유저] 내 정보 수정 (해시태그)
# @router.patch("/v1/gik-backend/my-profile/hashtag", status_code=status.HTTP_200_OK)


# # [유저] 내 정보 수정 (기본정보)
# @router.patch("/v1/gik-backend/my-profile/info", status_code=status.HTTP_200_OK)


# # [유저] 내 정보 수정 (fcm 코드)
# @router.patch("/v1/gik-backend/my-profile/fcm", status_code=status.HTTP_200_OK)


# # [유저] 내 정보 수정 (희망 관계)
# @router.patch("/v1/gik-backend/my-profile/relation", status_code=status.HTTP_200_OK)


# # [유저] 내 정보 수정 (포지션)
# @router.patch("/v1/gik-backend/my-profile/position", status_code=status.HTTP_200_OK)


# # [유저] 내 정보 수정 (알람)
# @router.patch("/v1/gik-backend/my-profile/alarm/{type}", status_code=status.HTTP_200_OK)


# # [유저] 상대 유저 상세정보 조회
# @router.get("v1/gik-backend/user/{user_id}", status_code=status.HTTP_200_OK)


# # [유저] 상대 유저 차단
# @router.patch("/v1/gik-backend/user/block", status_code=status.HTTP_200_OK)


# # [유저] 상대 유저 신고
# @router.patch("/v1/gik-backend/user/report", status_code=status.HTTP_200_OK)


# # [유저] 유저 목록으로 조회
# @router.get("/v1/gik-backend/users/list", status_code=status.HTTP_200_OK)


# # [유저] 유저 ID 목록 조회
# @router.get("/v1/gik-backend/users/id_list", status_code=status.HTTP_200_OK)


# # [유저] 유저 FCM 목록 조회
# @router.get("/v1/gik-backend/users/fcm_list", status_code=status.HTTP_200_OK)


# # [유저] 회원 탈퇴
# @router.delete("/v1/gik-backend/leave", status_code=status.HTTP_200_OK)
