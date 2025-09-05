from typing import *
from fastapi import (
    APIRouter,
    HTTPException,
    Form,
    UploadFile,
    status,
    File,
    Query,
    Depends,
    BackgroundTasks,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.db.community import (
    PostRequest,
    PostEditRequest,
    PostLikeRequest,
    PostBlockRequest,
    PostDeleteRequest,
    PostReportRequest,
    PostCommentRequest,
    CommentLikeRequest,
    CommentEditRequest,
    CommentDeleteRequest,
    CommentBlockRequest,
    CommentReportRequest,
    PostCommentRequestToken,
    PostLikeRequestToken,
)
from app.services.community_service import CommunityService
from app.services.push_service import PushService
from app.utils.token import get_user_id_from_token
from app.services.user_service import UserService
import uuid

oauth2_scheme = HTTPBearer()
router = APIRouter()
community_service = CommunityService()
user_service = UserService()
push_service = PushService()


# TODO : category, is_admin 컬럼 추가해서 전면 수정 필요 is_admin은 admin웹페이지에서 쓴 글만 true로, default NULL.
# [게시글] 게시글 등록
@router.post("/v1/gik-backend/community", status_code=status.HTTP_201_CREATED)
async def create_post(
    user_id: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
    category: Optional[str] = Form(default="talk"),
    images: Optional[List[UploadFile]] = File(default=[]),
):
    """
    게시글 등록
    userId: 게시글을 작성한 사용자 ID
    title: 게시글 제목
    content: 게시글 내용
    category: 게시글 카테고리
        - talk(자유·수다), meet(모집·소개), info(정보·공유), story(긱 스토리), event(2025 프라이드 엑스포)
    images: 게시글에 첨부할 이미지 리스트 (최대 x장)
    """

    post_id = await community_service.create_post(
        user_id=user_id, title=title, content=content, category=category, images=images
    )

    if not post_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="게시글 등록 실패"
        )
    return {"success": True, "message": "게시글 등록 성공", "postId": post_id}


# 카테고리는 수정이 안되는거라고 하셔서(수민님) 일단은 카테고리 수정은 제외함.
# [게시글] 게시글 수정
@router.patch("/v1/gik-backend/community/{post_id}", status_code=status.HTTP_200_OK)
async def edit_post(
    post_id: str,
    user_id: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
    url_list: Optional[List[str]] = Form(default=[]),
    images: List[UploadFile] = File(default=[]),
):
    """
    게시글 수정
    post_id: 수정할 게시글 ID
    title: 수정할 게시글 제목
    content: 수정할 게시글 내용
    url_list: 기존 이미지 URL 리스트 (수정 시 기존 이미지를 유지하기 위해 필요)
    images: 수정할 게시글에 첨부할 이미지 리스트 (최대 x장)
    """

    success = await community_service.edit_post(
        user_id=user_id,
        post_id=post_id,
        title=title,
        content=content,
        url_list=url_list,
        images=images,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="게시글 수정 실패"
        )

    return {"success": True, "message": "게시글 수정 성공"}


# TODO 라우터 경로설정 신경써야할듯. 현재 토큰이 따로 없어 user_id를 받아와야 하는 상황에서, delete메서드를 사용할 수 없어서 post로 사용하고, 라우터 경로를 delete로 임시저장.
# [게시글] 게시글 삭제
@router.post("/v1/gik-backend/community/delete", status_code=status.HTTP_200_OK)
async def delete_post(
    delete_request: PostDeleteRequest,
):
    """
    게시글 삭제
    post_id: 삭제할 게시글 ID
    """
    success = await community_service.delete_post(
        user_id=delete_request.userId, post_id=delete_request.postId
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="게시글 삭제 실패"
        )

    return {"success": True, "message": "게시글 삭제 성공"}


# TODO: 카테고리 별 list를 따로 불러올 필요가 있음.
# [게시글] 게시글 목록 불러오기
@router.get("/v1/gik-backend/community", status_code=status.HTTP_200_OK)
async def get_posts(
    page: int = Query(...),
    category: Optional[str] = Query(default=None),
):
    """
    게시글 목록 불러오기
    page: 페이지 인덱스 (1부터 시작, 20개씩 페이지네이션)
    """
    posts = await community_service.get_posts(page=page, category=category)

    return {"success": True, "message": "게시글 목록 불러오기 성공", "posts": posts}


# [게시글] 게시글 상세보기
@router.get("/v1/gik-backend/community/{post_id}", status_code=status.HTTP_200_OK)
async def get_post_detail(post_id: str):
    """
    게시글 상세보기
    post_id: 상세보기할 게시글 ID
    """
    post = await community_service.get_post_detail(post_id=post_id)

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="게시글을 찾을 수 없습니다."
        )

    return {"success": True, "message": "게시글 상세보기 성공", "post": post}


# [게시글] 게시글 검색
@router.get("/v1/gik-backend/community/search/{search}", status_code=status.HTTP_200_OK)
async def search_posts(search: str, category: Optional[str] = None):
    """
    게시글 검색
    search(수정 예정): 검색어
    """
    posts = await community_service.search_posts(search=search, category=category)
    return {"success": True, "message": "게시글 검색 성공", "posts": posts}


# TODO: snake_case로 변경 필요
# [게시글] 게시글 좋아요
@router.post("/v1/gik-backend/community/post/likes", status_code=status.HTTP_200_OK)
async def like_post(like_request: PostLikeRequest):
    """
    게시글 좋아요
    userId: 게시글을 좋아요한 사용자 ID
    postId: 좋아요할 게시글 ID
    """
    success = await community_service.like_post(
        userId=like_request.userId, postId=like_request.postId
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 좋아요 실패",
        )

    return {"success": True, "message": "게시글 좋아요 성공"}


# [게시글] 게시글 좋아요, 토큰으로 변경 및 push 전송
@router.post(
    "/v1/gik-backend/community/post/likes-token", status_code=status.HTTP_200_OK
)
async def like_post_with_push(
    post_id_request: PostLikeRequestToken,
    background_tasks: BackgroundTasks,
    token: str = Depends(oauth2_scheme),
):
    """
    게시글 좋아요(토큰 사용)
    token: 게시글을 좋아요한 사용자의 토큰
    """
    # 1. 해당 게시글에 좋아요를 누른 사람의 id 토큰에서 추출.
    viewer_id = await get_user_id_from_token(token.credentials)

    # 2. 해당 게시글에 좋아요 등록.
    success = await community_service.like_post(
        userId=viewer_id, postId=post_id_request.postId
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 좋아요 실패",
        )

    # 3-1. 푸시 전송을 위한 해당 게시글의 작성자 ID 조회.
    post_user_id = await community_service.fetch_post_user_id(post_id_request.postId)

    # 3-2. 만약 게시글 작성자와 좋아요를 누른 사람이 다를 경우에만 푸시 전송. 같으면 바로 return.
    if viewer_id != post_user_id:

        # 3-3. 푸시 로그 작성을 위한 작성자의 user_no조회
        target_user_no = await user_service.fetch_user_no(post_user_id)

        # 3-4. 푸시 전송을 위한 해당 게시글 작성자의 fcm 토큰 조회.
        target_token = await user_service.fetch_user_fcm(post_user_id)

        # 3-5. 좋아요 개수 조회
        like_count = await community_service.fetch_post_like_count(
            post_id_request.postId
        )

        push_id = str(uuid.uuid4())

        # 4. background task에 푸시 전송 작업 추가
        background_tasks.add_task(
            push_service.push_task,
            target_token,
            title="❤️내 게시글이 반응 폭발 중!",
            body=f"회원님의 게시글이 좋아요 {like_count}개를 돌파했어요. 지금 확인해 보세요!",
            data={
                "type": "postLike",
                "postId": post_id_request.postId,
                "pushId": push_id,
            },
            ttl_seconds=3600,
            collapse_key=f"post_like_{post_id_request.postId}",
            android_priority="high",
            mutable_content=True,
            content_available=True,
            user_no=target_user_no,
        )
    return {"success": True, "message": "게시글 좋아요 성공"}


# TODO: snake_case로 변경 필요
# [게시글] 게시글 좋아요 취소
@router.post(
    "/v1/gik-backend/community/post/cancel_likes", status_code=status.HTTP_200_OK
)
async def cancel_post_like(like_request: PostLikeRequest):
    """
    게시글 좋아요 취소
    userId: 게시글 좋아요 취소한 사용자 ID
    postId: 좋아요 취소할 게시글 ID
    """
    success = await community_service.cancel_post_like(
        userId=like_request.userId, postId=like_request.postId
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 좋아요 취소 실패",
        )

    return {"success": True, "message": "게시글 좋아요 취소 성공"}


# [게시글] 게시글 차단
@router.post("/v1/gik-backend/community/post/block", status_code=status.HTTP_200_OK)
async def block_post(block_request: PostBlockRequest):
    """
    게시글 차단
    userId: 게시글을 차단한 사용자 ID
    postId: 차단할 게시글 ID
    """
    success = await community_service.block_post(
        user_id=block_request.userId, post_id=block_request.blockPostId
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="게시글 차단 실패"
        )

    return {"success": success, "message": "게시글 차단 성공"}


# [게시글] 게시글 신고
@router.post("/v1/gik-backend/community/post/report", status_code=status.HTTP_200_OK)
async def report_post(report_request: PostReportRequest):
    """
    게시글 신고
    reportPostId: 신고할 게시글 ID
    reportUserId: 신고한 사용자 ID
    reason: 신고 사유
    """
    successs = await community_service.report_post(
        report_post_id=report_request.reportPostId,
        report_user_id=report_request.reportUserId,
        reason=report_request.reason,
    )
    if not successs:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="게시글 신고 실패"
        )

    return {"success": successs, "message": "게시글 신고 성공"}


# [게시글] 게시글 댓글 작성하기
@router.post("/v1/gik-backend/community/comments", status_code=status.HTTP_201_CREATED)
async def create_comment(comment_request: PostCommentRequest):
    """
    게시글 댓글 작성하기
    postId: 댓글을 작성할 게시글 ID
    userId: 댓글을 작성한 사용자 ID
    content: 댓글 내용
    """
    success = await community_service.create_comment(
        post_id=comment_request.postId,
        user_id=comment_request.userId,
        content=comment_request.content,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="댓글 작성 실패"
        )

    return {"success": success, "message": "댓글 작성 성공"}


@router.post(
    "/v1/gik-backend/community/comments-token", status_code=status.HTTP_201_CREATED
)
async def create_comment_with_push(
    comment_request: PostCommentRequestToken,
    background_tasks: BackgroundTasks,
    token: str = Depends(oauth2_scheme),
):
    """
    게시글 댓글 작성하기 (토큰 사용)
    token: 댓글을 작성한 사용자의 토큰
    """
    # 1. 토큰에서 댓글을 작성한 user_id 가져오기
    commenter_id = await get_user_id_from_token(token.credentials)

    # 2. 댓글 작성
    success = await community_service.create_comment(
        post_id=comment_request.postId,
        user_id=commenter_id,
        content=comment_request.content,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="댓글 작성 실패"
        )

    # 3-1. 푸시 작업을 위한 해당 게시글의 작성자 ID 조회.
    post_user_id = await community_service.fetch_post_user_id(comment_request.postId)

    # 3-2. 만약 댓글 작성자와 게시글 작성자가 다를 경우에만 푸시 전송. 같으면 바로 return.
    if commenter_id != post_user_id:
        # 3-3. 푸시를 보낼 작성자의 fcm 토큰 조회
        target_token = await user_service.fetch_user_fcm(post_user_id)

        # 3-4. 푸시 로그 작성을 위한 작성자의 user_no조회
        target_user_no = await user_service.fetch_user_no(post_user_id)

        # 4. background task에 푸시 전송 작업 추가
        push_id = str(uuid.uuid4())

        background_tasks.add_task(
            push_service.push_task,
            target_token,
            title="📩 새로운 댓글이 달렸어요!",
            body=f"내 글에 누군가 댓글을 남겼어요. 지금 확인해 보세요!",
            data={
                "type": "postComment",
                "postId": comment_request.postId,
                "pushId": push_id,
            },
            ttl_seconds=3600,
            collapse_key=f"post_comment_{comment_request.postId}",
            android_priority="high",
            mutable_content=True,
            content_available=True,
            user_no=target_user_no,
        )
    return {"success": success, "message": "댓글 작성 성공"}


# [게시글] 게시글 댓글 좋아요
@router.post("/v1/gik-backend/community/comment/likes", status_code=status.HTTP_200_OK)
async def like_comment(comment_like_request: CommentLikeRequest):
    """
    게시글 댓글 좋아요
    userId: 댓글을 좋아요한 사용자 ID
    commentId: 좋아요할 댓글 ID
    """
    success = await community_service.like_comment(
        user_id=comment_like_request.userId, comment_id=comment_like_request.commentId
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="댓글 좋아요 실패"
        )

    return {"success": success, "message": "댓글 좋아요 성공"}


# [게시글] 게시글 댓글 좋아요 취소
@router.post(
    "/v1/gik-backend/community/comment/cancel_likes", status_code=status.HTTP_200_OK
)
async def cancel_like_comment(comment_like_cancel_request: CommentLikeRequest):
    """
    게시글 댓글 좋아요 취소
    userId: 댓글 좋아요 취소한 사용자 ID
    commentId: 좋아요 취소할 댓글 ID
    """
    success = await community_service.cancel_like_comment(
        user_id=comment_like_cancel_request.userId,
        comment_id=comment_like_cancel_request.commentId,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="댓글 좋아요 취소 실패",
        )
    return {"success": success, "message": "댓글 좋아요 취소 성공"}


# [게시글] 게시글 댓글 삭제하기
@router.post(
    "/v1/gik-backend/community/comments/delete", status_code=status.HTTP_200_OK
)
async def delete_comment(comment_delete_request: CommentDeleteRequest):
    """
    게시글 댓글 삭제하기
    userId: 댓글을 삭제한 사용자 ID
    commentId: 삭제할 댓글 ID
    """
    success = await community_service.delete_comment(
        user_id=comment_delete_request.userId,
        comment_id=comment_delete_request.commentId,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="댓글 삭제 실패"
        )
    return {"success": success, "message": "댓글 삭제 성공"}


# [게시글] 게시글 댓글 목록 불러오기
@router.get(
    "/v1/gik-backend/community/comments/{post_id}", status_code=status.HTTP_200_OK
)
async def get_comments(post_id: str):
    """
    게시글 댓글 목록 불러오기
    post_id: 댓글 목록을 불러올 게시글 ID
    """
    success = await community_service.get_comments(post_id=post_id)

    return {"success": True, "message": "댓글 목록 불러오기 성공", "comments": success}


# TODO 게시글 댓글 수정은 이전 댓글의 데이터는 삭제하지 않는 것으로.
# [게시글] 게시글 댓글 수정하기
@router.patch(
    "/v1/gik-backend/community/comments/{comment_id}", status_code=status.HTTP_200_OK
)
async def edit_comment(comment_edit_request: CommentEditRequest):
    """
    게시글 댓글 수정하기
    userId: 댓글을 수정한 사용자 ID
    commentId: 수정할 댓글 ID
    content: 수정할 댓글 내용
    """
    success = await community_service.edit_comment(
        user_id=comment_edit_request.userId,
        comment_id=comment_edit_request.commentId,
        content=comment_edit_request.content,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="댓글 수정 실패"
        )
    return {"success": success, "message": "댓글 수정 성공"}


# [게시글] 내 게시글 불러오기
@router.post(
    "/v1/gik-backend/community/my-post/{user_id}", status_code=status.HTTP_200_OK
)
async def get_my_posts(user_id: str):
    """
    내 게시글 불러오기
    user_id: 게시글을 작성한 사용자 ID
    """
    success = await community_service.get_my_posts(user_id=user_id)

    return {"success": True, "message": "내 게시글 불러오기 성공", "posts": success}


# [게시글] 내 댓글 불러오기
@router.post(
    "/v1/gik-backend/community/my-comment/{user_id}", status_code=status.HTTP_200_OK
)
async def get_my_comments(user_id: str):
    """
    내 댓글 불러오기
    user_id: 댓글을 작성한 사용자 ID
    """
    success = await community_service.get_my_comments(user_id=user_id)

    return {"success": True, "message": "내 댓글 불러오기 성공", "comments": success}


# [게시글] 댓글 차단하기
@router.post("/v1/gik-backend/community/comment/block", status_code=status.HTTP_200_OK)
async def block_comment(block_request: CommentBlockRequest):
    """
    댓글 차단하기
    userId: 댓글을 차단한 사용자 ID
    commentId: 차단할 댓글 ID
    """
    success = await community_service.block_comment(
        user_id=block_request.userId, comment_id=block_request.commentId
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="댓글 차단 실패"
        )
    return {"success": success, "message": "댓글 차단 성공"}


# [게시글] 댓글 신고하기
@router.post("/v1/gik-backend/community/comment/report", status_code=status.HTTP_200_OK)
async def report_comment(report_request: CommentReportRequest):
    """
    댓글 신고하기
    reportCommentId: 신고할 댓글 ID
    reportUserId: 신고한 사용자 ID
    reason: 신고 사유
    """
    success = await community_service.report_comment(
        report_comment_id=report_request.reportCommentId,
        report_user_id=report_request.reportUserId,
        reason=report_request.reason,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="댓글 신고 실패"
        )

    return {"success": success, "message": "댓글 신고 성공"}
