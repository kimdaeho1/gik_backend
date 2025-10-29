from typing import Optional, List
from dependency_injector.wiring import inject, Provide
from fastapi import HTTPException, status, APIRouter, Depends, BackgroundTasks
from app.core.container import Container
from datetime import datetime

from app.db.chat import ChatPushRequest
from app.utils.token import get_user_id_from_token, JWTBearer
from app.services.push_service import PushService

oauth2_scheme = JWTBearer(auto_error=False)
router = APIRouter(prefix="/v1/gik-backend/chat", tags=["chat"])


@router.post("/send-push", status_code=status.HTTP_200_OK)
@inject
async def send_chat_push(
    background_tasks: BackgroundTasks,
    chat_request: ChatPushRequest,
    token: str = Depends(oauth2_scheme),
    push_service: PushService = Depends(Provide[Container.push_service]),
):
    result = await push_service.send_chat_push(
        chat_type=chat_request.chatType,
        chat_user_list=chat_request.chatUserList,
        chat_title=chat_request.chatTitle,
        chat_message=chat_request.chatMessage,
        token=token,
        background_tasks=background_tasks,
    )
    return {
        "success": True,
        "message": "채팅 푸시가 정상적으로 전송되었습니다.",
        "result": result,
    }
