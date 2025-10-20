from typing import List, Optional
from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, status, Depends, File, UploadFile, Query
from app.core.container import Container
from app.utils.token import get_user_id_from_token, JWTBearer
from app.db.feed import (
    CreateFeedRequest,
    UpdateFeedRequest,
    ReportFeedRequest,
    BlockFeedRequest,
)
from app.services.feed_service import FeedService

oauth2_scheme = JWTBearer(auto_error=False)
router = APIRouter(prefix="/v1/gik-backend/feed", tags=["Feed"])


# 피드는 사진, 글 둘중에 하나만 컨텐츠가 등록되어도 됨
# 피드 등록
@router.post("", status_code=status.HTTP_201_CREATED)
@inject
async def create_feed(
    create_feed_request: CreateFeedRequest,
    feed_images: Optional[List[UploadFile]] = File(default=[]),
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    result = await feed_service.create_feed(create_feed_request, feed_images, token)
    return {"success": result, "message": "피드가 성공적으로 게시되었습니다."}


# 피드 수정
@router.patch("/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def update_feed(
    feed_id: str,
    update_feed_request: UpdateFeedRequest,
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    result = await feed_service.update_feed()
    return {"success": result, "message": "피드가 성공적으로 수정되었습니다."}


# 피드 삭제
@router.delete("/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def delete_feed(
    feed_id: str,
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    result = await feed_service.delete_feed()
    return {"success": result, "message": "피드가 성공적으로 삭제되었습니다."}


# 피드 조회하기
@router.get("/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def get_feed(
    feed_id: str,
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    result = await feed_service.get_feed()
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
    result = await feed_service.report_feed()
    return {"success": result, "message": "피드가 성공적으로 신고되었습니다."}


# 피드 차단
@router.post("/block/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def block_feed(
    feed_id: str,
    block_feed_request: BlockFeedRequest,
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    result = await feed_service.block_feed()
    return {"success": result, "message": "피드가 성공적으로 차단되었습니다."}


# 피드 좋아요
@router.post("/like/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def like_feed(
    feed_id: str,
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    result = await feed_service.like_feed()
    return {"success": result, "message": "피드 좋아요가 성공적으로 처리되었습니다."}


# 피드 좋아요 취소
@router.post("/unlike/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def unlike_feed(
    feed_id: str,
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    result = await feed_service.unlike_feed()
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
    result = await service.get_my_feed_list()
    return {
        "success": True,
        "message": "내 피드 리스트를 성공적으로 가져왔습니다.",
        "feeds": result,
    }


# 피드 리스트 가져오기 - redis와 같은 캐싱을 사용해서 5개씩 가져오고, 로직 생각해보기.
@router.get("/list", status_code=status.HTTP_200_OK)
@inject
async def get_feed_list(
    page: int = Query(...),
    token: str = Depends(oauth2_scheme),
    service: FeedService = Depends(Provide[Container.feed_service]),
):
    result = await service.get_feed_list()
    return {
        "success": True,
        "message": "피드 리스트를 성공적으로 가져왔습니다.",
        "feeds": result,
    }
