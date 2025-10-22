from typing import List, Optional
from dependency_injector.wiring import inject, Provide

from fastapi import APIRouter, status, Depends
from app.core.container import Container
from app.utils.token import get_user_id_from_token, JWTBearer
from app.services.feed_comment_service import FeedCommentService
from app.db.feed_comment import (
    CreateFeedCommentRequest,
    UpdateFeedCommentRequest,
    ReportFeedCommentRequest,
)

oauth2_scheme = JWTBearer(auto_error=False)
router = APIRouter(prefix="/v1/gik-backend/feed/comment", tags=["Feed"])


# 피드 댓글 등록
@router.post("/{feed_id}", status_code=status.HTTP_201_CREATED)
@inject
async def create_feed_comment(
    feed_id: str,
    create_feed_comment_request: CreateFeedCommentRequest,
    token: str = Depends(oauth2_scheme),
    feed_comment_service: FeedCommentService = Depends(
        Provide[Container.feed_comment_service]
    ),
):
    result = await feed_comment_service.create_feed_comment(
        feed_id, create_feed_comment_request.content, token
    )
    return {"success": result, "message": "피드 댓글이 성공적으로 등록되었습니다."}


# 피드 댓글 수정
@router.patch("/{comment_id}", status_code=status.HTTP_200_OK)
@inject
async def update_feed_comment(
    comment_id: int,
    update_feed_comment_request: UpdateFeedCommentRequest,
    token: str = Depends(oauth2_scheme),
    feed_comment_service: FeedCommentService = Depends(
        Provide[Container.feed_comment_service]
    ),
):
    result = await feed_comment_service.update_feed_comment(
        comment_id, update_feed_comment_request.content, token
    )
    return {"success": result, "message": "피드 댓글이 성공적으로 수정되었습니다."}


# 피드 댓글 삭제
@router.delete("/{comment_id}", status_code=status.HTTP_200_OK)
@inject
async def delete_feed_comment(
    comment_id: int,
    token: str = Depends(oauth2_scheme),
    feed_comment_service: FeedCommentService = Depends(
        Provide[Container.feed_comment_service]
    ),
):
    result = await feed_comment_service.delete_feed_comment(comment_id, token)
    return {"success": result, "message": "피드 댓글이 성공적으로 삭제되었습니다."}


# 피드 댓글 차단
@router.post("/block/{comment_id}", status_code=status.HTTP_200_OK)
@inject
async def block_feed_comment(
    comment_id: int,
    token: str = Depends(oauth2_scheme),
    feed_comment_service: FeedCommentService = Depends(
        Provide[Container.feed_comment_service]
    ),
):
    result = await feed_comment_service.block_feed_comment(comment_id, token)
    return {"success": result, "message": "피드 댓글이 성공적으로 차단되었습니다."}


# 피드 댓글 신고
@router.post("/report/{comment_id}", status_code=status.HTTP_200_OK)
@inject
async def report_feed_comment(
    comment_id: int,
    report_feed_comment_request: ReportFeedCommentRequest,
    token: str = Depends(oauth2_scheme),
    feed_comment_service: FeedCommentService = Depends(
        Provide[Container.feed_comment_service]
    ),
):
    result = await feed_comment_service.report_feed_comment(
        comment_id,
        report_feed_comment_request.reportedUserId,
        report_feed_comment_request.reason,
        token,
    )
    return {"success": result, "message": "피드 댓글이 성공적으로 신고되었습니다."}


# 피드 댓글 리스트 조회
@router.get("/list/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def get_feed_comment_list(
    feed_id: str,
    token: str = Depends(oauth2_scheme),
    feed_comment_service: FeedCommentService = Depends(
        Provide[Container.feed_comment_service]
    ),
):
    result = await feed_comment_service.get_feed_comment_list(feed_id, token)
    return {
        "success": True,
        "message": "피드 댓글 리스트 조회에 성공했습니다.",
        "comments": result,
    }
