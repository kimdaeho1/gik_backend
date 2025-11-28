from typing import List
from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, HTTPException, Form, UploadFile, File, status, Query
from fastapi import BackgroundTasks, Depends
from typing import Optional
from app.db.biz import (
    BizAccountRequest,
    BizCouponRequest,
)
from app.services.user_service import UserService
from app.services.push_service import PushService
from app.repository.user_repository import UserRepository
from app.core.container import Container
from app.utils.token import get_user_id_from_token, JWTBearer
from app.db.db_connection import db
import uuid

oauth2_scheme = JWTBearer(auto_error=False)

router = APIRouter(prefix="/v1/gik-backend/biz", tags=["Biz"])


@router.post("/login")
@inject
async def login_biz_account(
    request_id: BizAccountRequest,
    biz_service=Depends(Provide[Container.biz_service]),
):
    access_token, refresh_token = await biz_service.login_biz_account(
        biz_id=request_id.biz_id,
        biz_password=request_id.biz_password,
    )
    return {
        "success": True,
        "message": "비즈 계정 로그인 성공",
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


@router.get("/info")
@inject
async def get_my_biz_account_info(
    token: str = Depends(oauth2_scheme),
    biz_service=Depends(Provide[Container.biz_service]),
):
    biz_info = await biz_service.get_my_biz_account_info(token=token)
    return {
        "success": True,
        "message": "비즈 계정 정보 조회 성공",
        "data": biz_info,
    }


@router.post("/upload-image")
@inject
async def upload_biz_images(
    biz_id: str = Form(...),
    biz_image: List[UploadFile] = File(...),
    biz_service=Depends(Provide[Container.biz_service]),
):
    image_urls = await biz_service.upload_biz_images(
        biz_id=biz_id,
        biz_image=biz_image,
    )
    return {
        "success": True,
        "message": "비즈 이미지 업로드 성공",
        "image_urls": image_urls,
    }


@router.post("/coupon")
@inject
async def create_biz_coupon(
    create_coupon_request: BizCouponRequest,
    token: str = Depends(oauth2_scheme),
    biz_service=Depends(Provide[Container.biz_service]),
):
    coupon = await biz_service.create_biz_coupon(
        token=token,
        title=create_coupon_request.title,
        content=create_coupon_request.content,
        start_date=create_coupon_request.start_date,
        expired_date=create_coupon_request.expired_date,
        amount=create_coupon_request.amount,
    )
    return {
        "success": True,
        "message": "비즈 쿠폰 생성 성공",
    }
