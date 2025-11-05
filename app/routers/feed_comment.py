from typing import List, Optional
from dependency_injector.wiring import inject, Provide

from fastapi import APIRouter, status, Depends, BackgroundTasks
from app.core.container import Container
from app.utils.token import get_user_id_from_token, JWTBearer
from app.services.feed_service import FeedService
from app.services.push_service import PushService
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
    background_tasks: BackgroundTasks,
    token: str = Depends(oauth2_scheme),
    feed_comment_service: FeedCommentService = Depends(
        Provide[Container.feed_comment_service]
    ),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
    push_service: PushService = Depends(Provide[Container.push_service]),
):
    await feed_comment_service.create_feed_comment(
        feed_id=feed_id, content=create_feed_comment_request.content, token=token
    )

    user_id = await get_user_id_from_token(token)

    feed_user_id = await feed_service.get_feed_user_id(feed_id=feed_id)

    # 피드의 시크릿 상태에 따라 푸시 타입 결정
    status = await feed_service.get_feed_status(feed_id=feed_id)
    if status == "feed":
        push_type = "feedComment"
    else:
        push_type = "secretFeedComment"

    image = await feed_service.get_feed_image(feed_id=feed_id)

    await push_service.send_push_to_user(
        background_tasks=background_tasks,
        user_id=feed_user_id,
        target_user_id=user_id,
        title_content="💭 새로운 댓글이 달렸어요!",
        body_content="내 피드에 누군가 댓글을 남겼어요. 지금 확인해 보세요!",
        data={
            "type": f"{push_type}",
            "feedId": feed_id,
            "feedImages": image,
        },
        collapse_key=f"feed_comment_{feed_id}",
        activity_type="feed_comment",
    )
    return {"success": True, "message": "피드 댓글이 성공적으로 등록되었습니다."}


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
    await feed_comment_service.update_feed_comment(
        comment_id=comment_id, content=update_feed_comment_request.content, token=token
    )
    return {"success": True, "message": "피드 댓글이 성공적으로 수정되었습니다."}


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
    await feed_comment_service.delete_feed_comment(comment_id=comment_id, token=token)
    return {"success": True, "message": "피드 댓글이 성공적으로 삭제되었습니다."}


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
    result = await feed_comment_service.block_feed_comment(
        comment_id=comment_id, token=token
    )
    return {"success": True, "message": "피드 댓글이 성공적으로 차단되었습니다."}


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
    await feed_comment_service.report_feed_comment(
        comment_id=comment_id,
        reported_user_id=report_feed_comment_request.reportedUserId,
        reason=report_feed_comment_request.reason,
        token=token,
    )
    return {"success": True, "message": "피드 댓글이 성공적으로 신고되었습니다."}


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
    result = await feed_comment_service.get_feed_comment_list(
        feed_id=feed_id, token=token
    )
    return {
        "success": True,
        "message": "피드 댓글 리스트 조회에 성공했습니다.",
        "comments": result,
    }
