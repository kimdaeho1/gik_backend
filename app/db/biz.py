from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from fastapi import Form


class BizAccountRequest(BaseModel):
    biz_id: str
    biz_password: str
