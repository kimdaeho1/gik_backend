from fastapi import (
    APIRouter,
    HTTPException,
    UploadFile,
    File,
    status,
    Form,
    BackgroundTasks,
    Depends,
    Query,
)
from typing import List
from app.utils.s3_upload import upload_file_to_s3
from PIL import Image
import io
from datetime import datetime
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.push_service import PushService
from app.services.image_service import ImageService
from app.services.user_service import UserService
from app.utils.token import get_user_id_from_token
from typing import Optional
import uuid

user_service = UserService()
image_service = ImageService()
push_service = PushService()
oauth2_scheme = HTTPBearer()
router = APIRouter()


def generate_filename(filename: str) -> str:
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S%f")[:-3]
    extension = filename.split(".")[-1] or "jpg"
    return f"{timestamp}.{extension}"


def image_url_list(
    s3_key: str,
    images: List[UploadFile],
):
    """
    이미지를 S3에 업로드 하고 url리스트를 반환
    """
    image_url_list = []
    try:
        for idx, file in enumerate(images):
            str_filename = generate_filename(file.filename)
            if not upload_file_to_s3(file.file, s3_key, str_filename):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload image {file.filename} to S3",
                )
            image_url_list.append(s3_key + str_filename)
        return image_url_list
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload images to S3 {str(e)}",
        )


@router.post("/v1/gik-backend/community/images", status_code=status.HTTP_200_OK)
async def upload_images(
    board_id: str = Form(...),
    images: List[UploadFile] = File(default=None),
):
    """
    게시판 이미지 업로드 (community/{게시판 ID}/)
    첫 번째 이미지는 섬네일로 다운사이징 해서 별도 저장 (community/{게시판 ID}/thumbnail/)
    """
    # 이미지 업로드후 리턴할 이미지 URL (원본이미지 3장인 image_url_list, 섬네일 이미지 thumbnail_url)
    image_url_list = []
    thumbnail_url = None
    try:
        for idx, file in enumerate(images):
            s3_key = f"community/{board_id}/"
            str_filename = generate_filename(file.filename)

            file.file.seek(0)
            image_files = file.file.read()
            origin_file = io.BytesIO(image_files)
            if not upload_file_to_s3(origin_file, s3_key, str_filename):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload image {file.filename} to S3",
                )
            # 원본 이미지 URL리스트에 추가
            image_url_list.append(s3_key + str_filename)

            # 첫 번재 이미지는 다운사이징 해서 섬네일로 저장하기.
            if idx == 0:
                image = Image.open(io.BytesIO(image_files))
                image.thumbnail((200, 200))
                thumb_io = io.BytesIO()
                image_format = image.format if image.format else "JPG"
                image.save(thumb_io, format=image_format)
                thumb_io.seek(0)

                thumbnail_s3_key = f"community/{board_id}/thumbnail/"
                thumbnail_filename = f"{board_id}_thumbnail.jpg"
                if not upload_file_to_s3(
                    thumb_io, thumbnail_s3_key, thumbnail_filename
                ):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to upload thumbnail for {file.filename} to S3 ",
                    )
                # 섬네일 이미지 URL
                thumbnail_url = thumbnail_s3_key + thumbnail_filename

        return {
            "message": "이미지 업로드 성공",
            "image_urls": image_url_list,
            "thumbnail_url": thumbnail_url,
        }
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload board images to S3 {str(e)}",
        )


@router.post("/v1/gik-backend/images", status_code=status.HTTP_200_OK)
async def upload_gik_images(
    user_id: str = Form(...),
    image_label: str = Form(...),
    images: List[UploadFile] = File(default=None),
):
    """
    유저 프로필 사진 업로드
    user_id: 이미지를 사용한 사용자의 id
    image_label: 이미지 사용처
        - user_profile: 유저 프로필 사진
    """

    s3_key = f"{image_label}/{user_id}/"
    image_urls = image_url_list(s3_key, images)
    return {"message": "이미지 업로드 성공", "image_urls": image_urls}


@router.post("/v1/gik-backend/chat/images", status_code=status.HTTP_200_OK)
async def upload_chat_images(
    chat_id: str = Form(...),
    image_label: str = Form(...),
    images: List[UploadFile] = File(default=None),
):
    """
    채팅방 이미지 업로드
    chat_id: 채팅방 ID
    image_label: 이미지 사용처
        - personal_chat: 1대1 채팅방에 업로드되는 사진
        - group_chat: 그룹 채팅방에 업로드되는 사진
    """

    s3_key = f"{image_label}/{chat_id}/"
    image_urls = image_url_list(s3_key, images)

    return {"message": "이미지 업로드 성공", "image_urls": image_urls}


@router.post("/v1/gik-backend/group-profile/images", status_code=status.HTTP_200_OK)
async def upload_group_profile_images(
    chat_id: str = Form(...),
    images: List[UploadFile] = File(default=None),
):
    """
    그룹 채팅 프로필 사진 업로드
    room_id: 그룹 채팅방 ID
    """

    s3_key = f"group_chat/{chat_id}/group_chat_profile/"
    image_urls = image_url_list(s3_key, images)
    return {"message": "그룹 채팅 프로필 사진 업로드 성공", "image_urls": image_urls}


# [시크릿] 시크릿 앨범 업로드
@router.post("/v1/gik-backend/secret/images", status_code=status.HTTP_200_OK)
async def upload_secret_images(
    token: str = Depends(oauth2_scheme),
    images: List[UploadFile] = File(default=None),
):
    """
    유저 시크릿 앨범 업로드
    user_id: token에서 추출, 시크릿 앨범 업로드 주체
    image: 이미지
    """
    user_id = await get_user_id_from_token(token.credentials)
    image_urls = await image_service.upload_user_secret_images(
        user_id=user_id, image=images
    )
    return {
        "success": True,
        "message": "시크릿 앨범 사진 업로드 성공",
        "image_urls": image_urls,
    }


# [시크릿] 시크릿 앨범 사진 수정
@router.post("/v1/gik-backend/secret/images/update", status_code=status.HTTP_200_OK)
async def update_secret_images(
    token: str = Depends(oauth2_scheme),
    image_index: Optional[List[str]] = Form(default=None),
    images: List[UploadFile] = File(default=None),
):
    """
    유저 시크릿 앨범 사진 수정
    user_id: token에서 추출, 시크릿 앨범 업로드 주체
    image_index: 수정할 이미지 인덱스 리스트
    image_lable: 이미지 사용처
        - user_secret_profile: 유저 시크릿 앨범 사진
    """
    user_id = await get_user_id_from_token(token.credentials)
    image_url_list = await image_service.update_user_secret_images(
        user_id=user_id, image_index=image_index, image=images
    )

    return {
        "success": True,
        "message": "시크릿 앨범 사진 수정 성공",
        "image_urls": image_url_list,
    }


# [시크릿] 상대 유저에게 시크릿 앨범 열람 요청
@router.post("/v1/gik-backend/secret/images/request", status_code=status.HTTP_200_OK)
async def request_user_secret_images(
    background_tasks: BackgroundTasks,
    token: str = Depends(oauth2_scheme),
    target_user_id: str = Query(...),
):
    """
    유저 시크릿 앨범 열람 요청
    user_id: token에서 추출, 시크릿 앨범 열람 요청 주체
    target_user_id: 시크릿 앨범 열람 요청 대상 유저 ID
    """
    # api를 호출한 사용자의 id
    user_id = await get_user_id_from_token(token.credentials)

    # fcm 토큰 가져오기
    target_token = await user_service.fetch_user_fcm(target_user_id)

    # api를 호출한 사용자의 닉네임 가져오기
    user_nickname = await user_service.fetch_user_nickname(user_id)

    # 푸시 로깅 작업 - 로그를 남기기 위한 유저의 no 가져오기
    target_user_no = await user_service.fetch_user_no(target_user_id)

    # 상대방이 나를 차단했다면
    is_blocked = await user_service.fetch_user_blocked(target_user_id, user_id)

    # 내 시크릿 앨범에 사진이 없다면
    is_image = await image_service.fetch_my_secret_images(user_id)
    if is_image is None:
        return {"success": False, "message": "내 시크릿 앨범에 사진이 없습니다."}

    if not is_blocked:
        # 푸시 전송
        push_id = str(uuid.uuid4())

        background_tasks.add_task(
            push_service.push_task,
            target_token,
            title="시크릿 앨범 열람 요청",
            body=f"{user_nickname}님이 회원님의 시크릿 앨범 열람을 요청했습니다.",
            data={"type": "secret", "requestId": user_id, "pushId": push_id},
            ttl_seconds=3600,
            collapse_key=f"secret-view-{user_id}",
            android_priority="high",
            mutable_content=True,
            content_available=True,
            user_no=target_user_no,
        )
        await image_service.request_user_secret_images(user_id, target_user_id)

    return {"success": True, "message": "시크릿 앨범 열람 요청 성공"}


# [시크릿] 상대 유저에게 시크릿 앨범 열람 수락
@router.patch("/v1/gik-backend/secret/images/accept", status_code=status.HTTP_200_OK)
async def accept_user_secret_images(
    background_tasks: BackgroundTasks,
    token: str = Depends(oauth2_scheme),
    target_user_id: str = Query(...),
):
    """
    유저 시크릿 앨범 열람 수락
    user_id: token에서 추출, 시크릿 앨범 열람 수락 주체
    target_user_id: 시크릿 앨범 열람 수락 대상 유저 ID
    """
    user_id = await get_user_id_from_token(token.credentials)

    # fcm 토큰 가져오기
    target_token = await user_service.fetch_user_fcm(target_user_id)

    # api를 호출한 사용자의 닉네임 가져오기
    user_nickname = await user_service.fetch_user_nickname(user_id)

    # 푸시 로깅 작업 - 로그를 남기기 위한 유저의 no 가져오기
    target_user_no = await user_service.fetch_user_no(target_user_id)

    # 상대방이 나를 차단했다면
    is_blocked = await user_service.fetch_user_blocked(target_user_id, user_id)

    if not is_blocked:
        # 푸시 전송
        push_id = str(uuid.uuid4())

        background_tasks.add_task(
            push_service.push_task,
            target_token,
            title="시크릿 앨범 열람 수락",
            body=f"{user_nickname}님이 회원님의 시크릿 앨범 열람 요청을 수락했습니다.",
            data={"type": "secret", "requestId": user_id, "pushId": push_id},
            ttl_seconds=3600,
            collapse_key=f"secret-view-{user_id}",
            android_priority="high",
            mutable_content=True,
            content_available=True,
            user_no=target_user_no,
        )
        await image_service.accept_user_secret_images(user_id, target_user_id)
    return {"success": True, "message": "시크릿 앨범 열람 수락 성공"}


# [시크릿] 상대 유저에게 시크릿 앨범 열람 거절
@router.patch("/v1/gik-backend/secret/images/reject", status_code=status.HTTP_200_OK)
async def reject_user_secret_images(
    token: str = Depends(oauth2_scheme),
    target_user_id: str = Query(...),
):
    """
    유저 시크릿 앨범 열람 거절
    user_id: token에서 추출, 시크릿 앨범 열람 거절 주체
    target_user_id: 시크릿 앨범 열람 거절 대상 유저 ID
    """
    user_id = await get_user_id_from_token(token.credentials)
    await image_service.reject_user_secret_images(user_id, target_user_id)
    return {"success": True, "message": "시크릿 앨범 열람 거절 성공"}


# [시크릿] 내 시크릿 앨범 요청 조회
@router.get("/v1/gik-backend/secret/images/requests", status_code=status.HTTP_200_OK)
async def fetch_my_secret_request(token: str = Depends(oauth2_scheme)):
    """
    유저 시크릿 요청
    user_id: token에서 추출, 시크릿 앨범 요청 목록 조회 주체
    """
    user_id = await get_user_id_from_token(token.credentials)
    requests = await image_service.fetch_my_secret_requests(user_id)
    return {
        "success": True,
        "message": "시크릿 앨범 요청 조회 성공",
        "requests": requests,
    }


# [시크릿] 내 시크릿 앨범 열람 승인건 조회
@router.get("/v1/gik-backend/secret/images/accepts", status_code=status.HTTP_200_OK)
async def fetch_my_secret_accepts(token: str = Depends(oauth2_scheme)):
    """
    유저 시크릿 앨범 열람 승인건 조회
    user_id: token에서 추출, 시크릿 앨범 열람 승인건 조회 주체
    """
    user_id = await get_user_id_from_token(token.credentials)
    accepts = await image_service.fetch_my_secret_accepts(user_id)
    return {
        "success": True,
        "message": "시크릿 앨범 열람 승인건 조회 성공",
        "accepts": accepts,
    }


# [시크릿] 내 시크릿 앨범 요청 취소
@router.patch("/v1/gik-backend/secret/images/cancel", status_code=status.HTTP_200_OK)
async def cancel_my_secret_request(
    token: str = Depends(oauth2_scheme),
    target_user_id: str = Query(...),
):
    """
    유저 시크릿 앨범 요청 취소
    user_id: token에서 추출, 시크릿 앨범 요청 취소 주체
    target_user_id: 시크릿 앨범 요청 취소 대상 유저 ID
    """
    user_id = await get_user_id_from_token(token.credentials)
    await image_service.cancel_my_secret_request(user_id, target_user_id)
    return {"success": True, "message": "시크릿 앨범 요청 취소 성공"}


# [시크릿] 내 시크릿 앨범 허용 취소
@router.patch(
    "/v1/gik-backend/secret/images/cancel-accept", status_code=status.HTTP_200_OK
)
async def cancel_accept_my_secret_request(
    token: str = Depends(oauth2_scheme),
    target_user_id: str = Query(...),
):
    """
    유저 시크릿 앨범 허용 취소
    user_id: token에서 추출, 시크릿 앨범 허용 취소 주체
    target_user_id: 시크릿 앨범 허용 취소 대상 유저 ID
    """
    user_id = await get_user_id_from_token(token.credentials)
    await image_service.cancel_accept_my_secret_request(user_id, target_user_id)
    return {"success": True, "message": "시크릿 앨범 허용 취소 성공"}


# [시크릿] 요청 수락된 시크릿 앨범 조회
@router.get("/v1/gik-backend/secret/images", status_code=status.HTTP_200_OK)
async def fetch_accepted_secret_images(
    token: str = Depends(oauth2_scheme),
    target_user_id: str = Query(...),
):
    """
    요청 수락된 시크릿 앨범 조회
    user_id: token에서 추출, 시크릿 앨범 조회 주체
    target_user_id: 시크릿 앨범 조회 대상 유저 ID
    """
    user_id = await get_user_id_from_token(token.credentials)
    image_urls = await image_service.fetch_accepted_secret_images(
        user_id, target_user_id
    )
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
