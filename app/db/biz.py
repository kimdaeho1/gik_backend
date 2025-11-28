from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from fastapi import Form


class BizAccountRequest(BaseModel):
    biz_id: str
    biz_password: str


class BizCouponRequest(BaseModel):
    title: str
    content: str
    start_date: Optional[str] = None
    expired_date: Optional[str] = None
    amount: Optional[int] = None
