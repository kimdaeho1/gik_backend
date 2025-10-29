from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ChatPushRequest(BaseModel):
    chatType: str
    chatUserList: List[str]
    chatTitle: Optional[str] = None
    chatMessage: str
