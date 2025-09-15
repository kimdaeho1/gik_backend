from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


class UserSecretResponse(BaseModel):
    userId: str
    requestId: str
    approveStatus: str
    createdAt: datetime
