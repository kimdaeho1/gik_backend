from typing import List, Optional
from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, status, Depends, File, UploadFile, Query
from app.core.container import Container
from app.utils.token import get_user_id_from_token, JWTBearer
from app.db.feed import (
    CreateFeedRequest,
    UpdateFeedRequest,
    ReportFeedRequest,
)
from app.services.feed_service import FeedService

oauth2_scheme = JWTBearer(auto_error=False)
router = APIRouter(prefix="/v1/gik-backend/feed", tags=["Feed"])


# 피드 수정/등록 API는 이미지 업로드가 포함되어 있기 때문에, 요청형식이 multipart/form-data가 된다.
# FastAPI에서는 JSON Body와 파일을 동시에 받을 수 없어서, 텍스트 필드는 Form으로, 이미지는 File로 받는다.
# 따라서, CreateFeedRequest와 UpdateFeedRequest의 모델에 @classmethod를 정의하고 라우터에서 Depend로 받기.
# 피드 등록
@router.post("", status_code=status.HTTP_201_CREATED)
@inject
async def create_feed(
    create_feed_request: CreateFeedRequest = Depends(
        CreateFeedRequest.create_feed_request
    ),
    feed_images: Optional[List[UploadFile]] = File(default=[]),
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    result = await feed_service.create_feed(
        token,
        create_feed_request.content,
        create_feed_request.secretStatus,
        create_feed_request.status,
        feed_images,
    )
    return {"success": result, "message": "피드가 성공적으로 게시되었습니다."}


# 피드 수정
@router.patch("/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def update_feed(
    feed_id: str,
    update_feed_request: UpdateFeedRequest = Depends(
        UpdateFeedRequest.update_feed_request
    ),
    update_feed_images: Optional[List[UploadFile]] = File(default=[]),
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    """
    유저 피드 업데이트
    - feed_id: 수정할 피드의 ID
    - content: 피드 내용 (선택 사항)
    - imageUrl: 수정하지 않을 이미지 URL 리스트 (선택 사항)
    - status: 피드 공개 여부
    - secretStatus: 피드 비밀 여부
    - update_feed_images: 새로 추가할 이미지 파일 리스트 (선택 사항)
    """
    result = await feed_service.update_feed(
        token,
        feed_id,
        update_feed_request.content,
        update_feed_request.imageUrl,
        update_feed_request.status,
        update_feed_request.secretStatus,
        update_feed_images,
    )
    return {"success": result, "message": "피드가 성공적으로 수정되었습니다."}


# 피드 삭제
@router.delete("/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def delete_feed(
    feed_id: str,
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    result = await feed_service.delete_feed(token, feed_id)
    return {"success": result, "message": "피드가 성공적으로 삭제되었습니다."}


# 내가 차단한사람의 피드와, 내가 차단한 피드는 둘다 보이지 않아야 한다.
# 피드 리스트 가져오기 - redis와 같은 캐싱을 사용해서 5개씩 가져오고, 로직 생각해보기.
@router.get("/list", status_code=status.HTTP_200_OK)
@inject
async def get_feed_list(
    page: int = Query(...),
    token: str = Depends(oauth2_scheme),
    service: FeedService = Depends(Provide[Container.feed_service]),
):
    result = await service.get_feed_list(
        token,
        page,
    )
    return {
        "success": True,
        "message": "피드 리스트를 성공적으로 가져왔습니다.",
        "feeds": result,
    }


# 피드 조회하기
@router.get("/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def get_feed(
    feed_id: str,
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    result = await feed_service.get_feed(token, feed_id)
    return {
        "success": True,
        "message": "피드 조회에 성공했습니다.",
        "feed": result,
    }


# 피드 신고
@router.post("/report/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def report_feed(
    feed_id: str,
    report_feed_request: ReportFeedRequest,
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    result = await feed_service.report_feed(
        token,
        feed_id,
        report_feed_request.reportedUserId,
        report_feed_request.reason,
    )
    return {"success": result, "message": "피드가 성공적으로 신고되었습니다."}


# 피드 차단
@router.post("/block/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def block_feed(
    feed_id: str,
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    result = await feed_service.block_feed(
        token,
        feed_id,
    )
    return {"success": result, "message": "피드가 성공적으로 차단되었습니다."}


# 피드 좋아요
@router.post("/like/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def like_feed(
    feed_id: str,
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    result = await feed_service.like_feed(token, feed_id)
    return {"success": result, "message": "피드 좋아요가 성공적으로 처리되었습니다."}


# 피드 좋아요 취소
@router.post("/unlike/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def unlike_feed(
    feed_id: str,
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    result = await feed_service.unlike_feed(token, feed_id)
    return {
        "success": result,
        "message": "피드 좋아요 취소가 성공적으로 처리되었습니다.",
    }


# 내 피드 리스트 가져오기
@router.get("/my-feed/list", status_code=status.HTTP_200_OK)
@inject
async def get_my_feed_list(
    page: int = Query(...),
    token: str = Depends(oauth2_scheme),
    service: FeedService = Depends(Provide[Container.feed_service]),
):
    result = await service.get_my_feed_list(token, page)
    return {
        "success": True,
        "message": "내 피드 리스트를 성공적으로 가져왔습니다.",
        "feeds": result,
    }
