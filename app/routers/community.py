from typing import *
from fastapi import APIRouter, HTTPException, Form, UploadFile, status, File, Query
from app.db.community import PostRequest, PostEditRequest, PostLikeRequest, PostBlockRequest, PostDeleteRequest, PostReportRequest, PostCommentRequest, CommentLikeRequest, CommentEditRequest, CommentDeleteRequest
from app.services.community_service import CommunityService


router = APIRouter()
community_service = CommunityService()


# [게시글] 게시글 등록
@router.post("/v1/gik-backend/community", status_code=status.HTTP_201_CREATED)
async def create_post(
    user_id: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
    images: Optional[List[UploadFile]] = File(default=[])
):
    """
    게시글 등록
    userId: 게시글을 작성한 사용자 ID
    title: 게시글 제목
    content: 게시글 내용
    images: 게시글에 첨부할 이미지 리스트 (최대 x장)
    """
    
    post_id = await community_service.create_post(
        user_id=user_id,
        title=title,
        content=content,
        images=images
    )
    
    if not post_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 등록 실패"
        )
    return {"success": True, "message": "게시글 등록 성공", "postId": post_id}


# [게시글] 게시글 수정
@router.patch("/v1/gik-backend/community/{post_id}", status_code=status.HTTP_200_OK)
async def edit_post(
    post_id: str,
    user_id: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
    images: List[UploadFile] = File(default=[])
):
    """
    게시글 수정
    post_id: 수정할 게시글 ID
    title: 수정할 게시글 제목
    content: 수정할 게시글 내용
    images: 수정할 게시글에 첨부할 이미지 리스트 (최대 x장)
    """
    
    success = await community_service.edit_post(
        user_id=user_id,
        post_id=post_id,
        title=title,
        content=content,
        images=images
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 수정 실패"
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
        user_id=delete_request.userId,
        post_id=delete_request.postId
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 삭제 실패"
        )
    
    return {"success": True, "message": "게시글 삭제 성공"}


# [게시글] 게시글 목록 불러오기
@router.get("/v1/gik-backend/community", status_code=status.HTTP_200_OK)
async def get_post(
    page: int = Query(...)
):
    """
    게시글 목록 불러오기
    page: 페이지 인덱스 (1부터 시작, 20개씩 페이지네이션)
    """
    posts = await community_service.get_posts(page=page)
    
    if not posts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다."
        )
    
    return {"success": True, "message": "게시글 목록 불러오기 성공", "posts": posts}
    


# [게시글] 게시글 상세보기
@router.get("/v1/gik-backend/community/{post_id}", status_code=status.HTTP_200_OK)
async def get_post_detail(
    post_id: str
):
    """
    게시글 상세보기
    post_id: 상세보기할 게시글 ID
    """
    post = await community_service.get_post_detail(post_id=post_id)
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다."
        )
    
    return {"success": True, "message": "게시글 상세보기 성공", "post": post}


# [게시글] 게시글 검색
@router.get("/v1/gik-backend/community/search/{search}", status_code=status.HTTP_200_OK)
async def search_posts(
    search: str
):
    """
    게시글 검색
    search(수정 예정): 검색어
    """
    
    posts = await community_service.search_posts(search=search)
    if not posts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="검색 결과가 없습니다."
        )
    return {"success": True, "message": "게시글 검색 성공", "posts": posts}
    
# TODO: snake_case로 변경 필요
# [게시글] 게시글 좋아요
@router.post("/v1/gik-backend/community/post/likes", status_code=status.HTTP_200_OK)
async def like_post(
    like_request: PostLikeRequest
):
    """
    게시글 좋아요
    userId: 게시글을 좋아요한 사용자 ID
    postId: 좋아요할 게시글 ID
    """
    success = await community_service.like_post(
        userId=like_request.userId,
        postId=like_request.postId
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 좋아요 실패"
        )
    
    return {"success": True, "message": "게시글 좋아요 성공"}
    

# TODO: snake_case로 변경 필요
# [게시글] 게시글 좋아요 취소
@router.post("/v1/gik-backend/community/post/cancel_likes", status_code=status.HTTP_200_OK)
async def cancel_post_like(
    like_request: PostLikeRequest
):
    """
    게시글 좋아요 취소
    userId: 게시글 좋아요 취소한 사용자 ID
    postId: 좋아요 취소할 게시글 ID
    """
    success = await community_service.cancel_post_like(
        userId=like_request.userId,
        postId=like_request.postId
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 좋아요 취소 실패"
        )
    
    return {"success": True, "message": "게시글 좋아요 취소 성공"}


# [게시글] 게시글 차단
@router.patch("/v1/gik-backend/community/post/block", status_code=status.HTTP_200_OK)
async def block_post(
    block_request: PostBlockRequest
):
    """
    게시글 차단
    userId: 게시글을 차단한 사용자 ID
    postId: 차단할 게시글 ID
    """
    success = await community_service.block_post(
        user_id=block_request.userId,
        post_id=block_request.blockPostId
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 차단 실패"
        )

    return {"success": success, "message": "게시글 차단 성공"}


# [게시글] 게시글 신고
@router.patch("/v1/gik-backend/community/post/report", status_code=status.HTTP_200_OK)
async def report_post(
    report_request: PostReportRequest
):
    """
    게시글 신고
    reportPostId: 신고할 게시글 ID
    reportUserId: 신고한 사용자 ID
    reason: 신고 사유
    """
    successs = await community_service.report_post(
        report_post_id=report_request.reportPostId,
        report_user_id=report_request.reportUserId,
        reason=report_request.reason
    )
    if not successs:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 신고 실패"
        )
        
    return {"success": successs, "message": "게시글 신고 성공"}


# [게시글] 게시글 댓글 작성하기
@router.post("/v1/gik-backend/community/comments", status_code=status.HTTP_201_CREATED)
async def comment_post(
    comment_request: PostCommentRequest
):
    """
    게시글 댓글 작성하기
    postId: 댓글을 작성할 게시글 ID
    userId: 댓글을 작성한 사용자 ID
    content: 댓글 내용
    """
    success = await community_service.create_comment(
        post_id=comment_request.postId,
        user_id=comment_request.userId,
        content=comment_request.content
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="댓글 작성 실패"
        )
    
    return {"success": success, "message": "댓글 작성 성공"}





# [게시글] 게시글 댓글 좋아요
@router.post("/v1/gik-backend/community/comment/likes", status_code=status.HTTP_200_OK)
async def like_comment(
    comment_like_request: CommentLikeRequest
):
    """
    게시글 댓글 좋아요
    userId: 댓글을 좋아요한 사용자 ID
    commentId: 좋아요할 댓글 ID
    """
    success = await community_service.like_comment(
        user_id=comment_like_request.userId,
        comment_id=comment_like_request.commentId
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="댓글 좋아요 실패"
        )
    
    return {"success": success, "message": "댓글 좋아요 성공"}
    


# [게시글] 게시글 댓글 좋아요 취소
@router.post("/v1/gik-backend/community/comment/cancel_likes", status_code=status.HTTP_200_OK)
async def cancel_like_comment(
    comment_like_cancel_request: CommentLikeRequest
):
    """
    게시글 댓글 좋아요 취소
    userId: 댓글 좋아요 취소한 사용자 ID
    commentId: 좋아요 취소할 댓글 ID
    """
    success = await community_service.cancel_like_comment(
        user_id=comment_like_cancel_request.userId,
        comment_id=comment_like_cancel_request.commentId
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="댓글 좋아요 취소 실패"
        )
    return {"success": success, "message": "댓글 좋아요 취소 성공"}


# [게시글] 게시글 댓글 삭제하기
@router.post("/v1/gik-backend/community/comments/delete", status_code=status.HTTP_200_OK)
async def delete_comment(
    comment_delete_request: CommentDeleteRequest
):
    """
    게시글 댓글 삭제하기
    userId: 댓글을 삭제한 사용자 ID
    commentId: 삭제할 댓글 ID
    """
    success = await community_service.delete_comment(
        user_id=comment_delete_request.userId,
        comment_id=comment_delete_request.commentId
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="댓글 삭제 실패"
        )
    return {"success": success, "message": "댓글 삭제 성공"}


# [게시글] 게시글 댓글 목록 불러오기
# TODO: 페이지네이션 있어야하는지?
@router.get("/v1/gik-backend/community/comments/{post_id}", status_code=status.HTTP_200_OK)
async def get_comments(
    post_id: str
):
    """
    게시글 댓글 목록 불러오기
    post_id: 댓글 목록을 불러올 게시글 ID
    """
    success = await community_service.get_comments(post_id=post_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="댓글 목록 불러오기 실패."
        )
    
    return {"success": True, "message": "댓글 목록 불러오기 성공", "comments": success }


# TODO 게시글 댓글 수정은 이전 댓글의 데이터는 삭제하지 않는 것으로.
# [게시글] 게시글 댓글 수정하기
@router.patch("/v1/gik-backend/community/comments/{comment_id}", status_code=status.HTTP_200_OK)
async def edit_comment(
    comment_edit_request: CommentEditRequest
):
    """
    게시글 댓글 수정하기
    userId: 댓글을 수정한 사용자 ID
    commentId: 수정할 댓글 ID
    content: 수정할 댓글 내용
    """
    success = await community_service.edit_comment(
        user_id=comment_edit_request.userId,
        comment_id=comment_edit_request.commentId,
        content=comment_edit_request.content
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="댓글 수정 실패"
        )
    return {"success": success, "message": "댓글 수정 성공"}
