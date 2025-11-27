from typing import List
from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, HTTPException, Form, UploadFile, File, status, Query
from fastapi import BackgroundTasks, Depends
from typing import Optional
from app.db.biz import (
    BizAccountRequest,
)
from app.services.user_service import UserService
from app.services.push_service import PushService
from app.repository.user_repository import UserRepository
from app.core.container import Container
from app.utils.token import get_user_id_from_token, JWTBearer
from app.db.db_connection import db
import uuid

oauth2_scheme = JWTBearer(auto_error=False)

router = APIRouter(prefix="/biz", tags=["Biz"])


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
