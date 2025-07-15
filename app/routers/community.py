from typing import *
from fastapi import APIRouter, HTTPException, Form, UploadFile, status  

router = APIRouter()

# [게시글] 게시글 등록
@router.post("/v1/gik-backend/community", status_code=status.HTTP_201_CREATED)


# [게시글] 게시글 수정
@router.patch("/v1/gik-backend/community/{post_id}", status_code=status.HTTP_200_OK)


# [게시글] 게시글 삭제
@router.delete("/v1/gik-backend/community/{post_id}", status_code=status.HTTP_200_OK)


# [게시글] 게시글 목록 불러오기
@router.get("/v1/gik-backend/community", status_code=status.HTTP_200_OK)


# [게시글] 게시글 상세보기
@router.get("/v1/gik-backend/community/{post_id}", status_code=status.HTTP_200_OK)


# [게시글] 게시글 좋아요
@router.post("/v1/gik-backend/community/likes", status_code=status.HTTP_200_OK)


# [게시글] 게시글 차단
@router.patch("/v1/gik-backend/community/block", status_code=status.HTTP_200_OK)


# [게시글] 게시글 신고
@router.patch("/v1/gik-backend/community/report", status_code=status.HTTP_200_OK)


# [게시글] 게시글 댓글 작성하기
@router.post("/v1/gik-backend/community/comments", status_code=status.HTTP_201_CREATED)


# [게시글] 게시글 댓글 수정하기
@router.patch("/v1/gik-backend/community/comments/{comment_id}", status_code=status.HTTP_200_OK)


# [게시글] 게시글 댓글 삭제하기
@router.delete("/v1/gik-backend/community/comments/{comment_id}", status_code=status.HTTP_200_OK)
