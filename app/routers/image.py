from fastapi import APIRouter, HTTPException, UploadFile, File, status, Form
from typing import List
from app.utils.s3_upload import upload_file_to_s3
from PIL import Image
import io
from datetime import datetime

router = APIRouter()

def generate_filename(filename: str) -> str:
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S%f")[:-3]
    extension = filename.split('.')[-1] or "jpg"
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
            s3_key=f"community/{board_id}/"
            str_filename = generate_filename(file.filename)
            
            file.file.seek(0)
            image_files = file.file.read()
            origin_file=io.BytesIO(image_files)
            if not upload_file_to_s3(origin_file, s3_key, str_filename):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload image {file.filename} to S3",
                )
            # 원본 이미지 URL리스트에 추가
            image_url_list.append(s3_key + str_filename)

            # 첫 번재 이미지는 다운사이징 해서 섬네일로 저장하기.
            if idx == 0:
                image=Image.open(io.BytesIO(image_files))
                image.thumbnail((200, 200))
                thumb_io = io.BytesIO()
                image_format = image.format if image.format else "JPG"
                image.save(thumb_io, format=image_format)
                thumb_io.seek(0)

                thumbnail_s3_key = f"community/{board_id}/thumbnail/"
                thumbnail_filename = f"{board_id}_thumbnail.jpg"
                if not upload_file_to_s3(thumb_io, thumbnail_s3_key, thumbnail_filename):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to upload thumbnail for {file.filename} to S3 ",
                    )
                # 섬네일 이미지 URL
                thumbnail_url = thumbnail_s3_key + thumbnail_filename

        return {"message": "이미지 업로드 성공", "image_urls": image_url_list, "thumbnail_url": thumbnail_url}
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
    room_id: str = Form(...),
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
    room_id: str = Form(...),
    images: List[UploadFile] = File(default=None),
):
    """
    그룹 채팅 프로필 사진 업로드
    room_id: 그룹 채팅방 ID
    """

    s3_key = f"group_chat/{room_id}/group_chat_profile/"
    image_urls = image_url_list(s3_key, images)
    return {"message": "그룹 채팅 프로필 사진 업로드 성공", "image_urls": image_urls}
