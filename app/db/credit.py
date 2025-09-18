from datetime import datetime
from pydantic import BaseModel


class CreditValues:
    # TODO: 나중에 수정 필요
    RECOMMEND_REJECT = 5  # 시스템에게 추천받은 프로필 거절
    LIKE_REJECT = 20  # 상대방에게 받은 호감 거절
    LIKE_SENT = 20  # 상대방에게 호감 발송
    LIKE_CONFIRM = 100  # 상대방 호감 수락

    WHOIS_VIEW = 1  # 누가 나를 봤는지


class CreditHistory(BaseModel):
    amount: int
    description: str
    created_at: datetime

    # reg_dt를 ISO 포맷으로 변환
    # @field_validator("created_at", mode="before")
    # def date_to_str(cls, v):
    #     if isinstance(v, date):
    #         return v.strftime("%Y-%m-%d %H:%M:%S")
    #     return v
