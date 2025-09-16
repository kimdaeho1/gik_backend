from pydantic import BaseModel
from datetime import datetime


class UserSecretResponse(BaseModel):
    userId: str
    requestId: str
    approveStatus: str
    createdAt: datetime
