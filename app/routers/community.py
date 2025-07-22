from typing import *
from fastapi import APIRouter, HTTPException, Form, UploadFile, status, File, Query
from app.db.community import PostRequest, PostEditRequest, PostLikeRequest, PostBlockRequest
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


# [게시글] 게시글 삭제
@router.post("/v1/gik-backend/community/{post_id}", status_code=status.HTTP_200_OK)
async def delete_post(
    post_id: str
):
    """
    게시글 삭제
    post_id: 삭제할 게시글 ID
    """
    success = await community_service.delete_post(post_id=post_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 삭제 실패"
        )
    
    return {"success": True, "message": "게시글 삭제 성공"}

# [게시글] 게시글 목록 불러오기
# 20개씩 끊어서 페이지네이션.
@router.get("/v1/gik-backend/community", status_code=status.HTTP_200_OK)
async def get_post(
    index: int = Query(...)
):
    """
    게시글 목록 불러오기
    index: 페이지 인덱스 (1부터 시작, 20개씩 페이지네이션)
    """
    posts = await community_service.get_posts(index=index)
    
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
    
    
# [게시글] 게시글 좋아요
@router.post("/v1/gik-backend/community/likes", status_code=status.HTTP_200_OK)
async def like_post(
      
):
    ...


# [게시글] 게시글 좋아요 취소
@router.patch("/v1/gik-backend/community/cancel_likes", status_code=status.HTTP_200_OK)
async def cancel_like_post(
    
):
    ...
    

# [게시글] 게시글 차단
@router.patch("/v1/gik-backend/community/block", status_code=status.HTTP_200_OK)
async def block_post(
    
):
    ...


# [게시글] 게시글 신고
@router.patch("/v1/gik-backend/community/report", status_code=status.HTTP_200_OK)
async def report_post(
    
):
    ...


# [게시글] 게시글 댓글 작성하기
@router.post("/v1/gik-backend/community/comments", status_code=status.HTTP_201_CREATED)
async def comment_post(
    
):
    ...


# [게시글] 게시글 댓글 목록 불러오기
@router.get("/v1/gik-backend/community/comments", status_code=status.HTTP_200_OK)
async def get_comments(
    
):
    ...


# [게시글] 게시글 댓글 수정하기
@router.patch("/v1/gik-backend/community/comments/{comment_id}", status_code=status.HTTP_200_OK)
async def edit_comment(
    
):
    ...

# [게시글] 게시글 댓글 삭제하기
@router.delete("/v1/gik-backend/community/comments/{comment_id}", status_code=status.HTTP_200_OK)
async def delete_comment(
    
):
    ...


# [게시글] 게시글 댓글 좋아요
@router.post("/v1/gik-backend/community/comment/likes", status_code=status.HTTP_200_OK)
async def like_comment(
    
):
    ...
    

# [게시글] 게시글 댓글 좋아요 취소
@router.patch("/v1/gik-backend/community/comment/cancel_likes", status_code=status.HTTP_200_OK)
async def cancel_like_comment(
    
):
    ...