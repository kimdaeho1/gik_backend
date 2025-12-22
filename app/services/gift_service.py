from app.db.db_connection import db
from app.repository.user_repository import UserRepository
from app.repository.gift_repository import GiftRepository
from app.db.gift import GifticonProductResponse, GifticonDetailResponse
from typing import List, Optional
import httpx, math
from fastapi import HTTPException
from app.utils.logging_config import get_logger
from app.utils.config import CUSTOM_AUTH_CODE, CUSTOM_AUTH_TOKEN
from app.utils.token import get_user_id_from_token
from datetime import datetime
import uuid

logger = get_logger(__name__)


# 기프티쇼의 tr_id 필수. 형식: gift_YYYYMMDDHHMMSS_사용자ID끝6자리
def generate_tr_id() -> str:
    now = datetime.now()
    date_part = now.strftime("%Y%m%d")
    micro = now.strftime("%f")
    millis_7 = f"{micro}0"[:7]

    return f"service_{date_part}_{millis_7}"


class GiftService:
    def __init__(
        self,
        user_repository: UserRepository,
        gift_repository: GiftRepository,
    ):
        self.user_repository = user_repository
        self.gift_repository = gift_repository

    async def get_gifticon_goods(
        self, page: int, brand_name: Optional[str] = None
    ) -> List[GifticonProductResponse]:
        goods_list = await self.gift_repository.get_gifticon_goods(
            page=page, brand_name=brand_name
        )

        return [
            GifticonProductResponse(
                goodsCode=goods["goods_code"],
                brandName=goods["brand_name"],
                goodsName=goods["goods_name"],
                content=goods["content"],
                imageUrl=goods["image_url"],
                imageThumbUrl=goods["image_thumb"],
                priceReal=goods["price_real"],
                priceSupply=goods["price_supply"],
                goodsState=goods["goods_state"],
                isActive=goods["is_active"],
                limitDays=goods["limit_days"],
                validEndDate=goods["valid_end_date"],
                coinPrice=math.ceil(goods["price_real"] / 50),
            )
            for goods in goods_list
        ]

    async def get_gifticon_goods_detail(
        self, goods_detail: dict
    ) -> GifticonDetailResponse:

        return GifticonDetailResponse(
            mdCode=goods_detail.get("mdCode", ""),
            discountPrice=goods_detail.get("discountPrice", 0),
            mmsGoodsImg=goods_detail.get("mmsGoodsImg", ""),
            limitDay=goods_detail.get("limitDay", 0),
            content=goods_detail.get("content", ""),
            goodsDescImgWeb=goods_detail.get("goodsDescImgWeb", ""),
            goodsImgB=goods_detail.get("goodsImgB", ""),
            goodsTypeNm=goods_detail.get("goodsTypeNm", ""),
            categoryName1=goods_detail.get("categoryName1", ""),
            goodsName=goods_detail.get("goodsName", ""),
            mmsReserveFlag=goods_detail.get("mmsReserveFlag", ""),
            goodsStateCd=goods_detail.get("goodsStateCd", ""),
            brandCode=goods_detail.get("brandCode", ""),
            goodsNo=goods_detail.get("goodsNo", 0),
            brandName=goods_detail.get("brandName", ""),
            brandIconImg=goods_detail.get("brandIconImg", ""),
            goodsTypeCd=goods_detail.get("goodsTypeCd", ""),
            saleDateFlagCd=goods_detail.get("saleDateFlagCd", ""),
            contentAddDesc=goods_detail.get("contentAddDesc", ""),
            categorySeq1=goods_detail.get("categorySeq1", 0),
            goodsCode=goods_detail.get("goodsCode", ""),
            goodsTypeDtlNm=goods_detail.get("goodsTypeDtlNm", ""),
            goodsImgS=goods_detail.get("goodsImgS", ""),
            affiliate=goods_detail.get("affiliate", ""),
            saleDateFlag=goods_detail.get("saleDateFlag", ""),
            realPrice=goods_detail.get("realPrice", 0),
            coinPrice=math.ceil(goods_detail.get("realPrice", 0) / 50),
        )

    async def get_goods_category_list(
        self,
    ) -> List[str]:
        category_list = await self.gift_repository.get_goods_category_list()

        return category_list

    async def get_category_brand_list(self, category: str) -> List[str]:
        brand_list = await self.gift_repository.get_category_brand_list(
            category=category
        )

        return brand_list

    async def purchase_gifticon_goods(self, token: str, goods_code: str):
        user_id = await get_user_id_from_token(token=token)
        tr_id = generate_tr_id()

        purchase = await self.gift_repository.create_purchase(
            user_id=user_id, tr_id=tr_id, goods_code=goods_code
        )

        try:
            await self.send_giftishow_coupon(
                tr_id=tr_id, user_id=user_id, goods_code=goods_code
            )
            await self.gift_repository.mark_sent(tr_id=tr_id)
        except Exception:
            await self.cancel_giftishow_coupon(tr_id=tr_id, user_id=user_id)
            await self.gift_repository.cancel_purchase(
                tr_id=tr_id, user_id=user_id, refund_credit=purchase["price_credit"]
            )
            raise HTTPException(
                status_code=502, detail="기프티콘 전송 실패, 구매가 취소되었습니다."
            )

    async def send_giftishow_coupon(self, tr_id: str, user_id: str, goods_code: str):
        user_phone_number = await self.gift_repository.get_user_phone_number(user_id)
        if not user_phone_number:
            raise HTTPException(status_code=400, detail="사용자 전화번호가 없습니다.")
        payload = {
            "api_code": "0204",
            "custom_auth_code": CUSTOM_AUTH_CODE,
            "custom_auth_token": CUSTOM_AUTH_TOKEN,
            "dev_yn": "N",
            "goods_code": goods_code,
            "mms_msg": "기프티콘이 도착했습니다.",
            "mms_title": "기프티콘",
            "callback_no": "15776474",
            "phone_no": user_phone_number.replace("-", ""),
            "tr_id": tr_id,
            "user_id": "ask@couplematch.co.kr",
            "gubun": "N",
        }

        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post(
                "https://bizapi.giftishow.com/bizApi/send",
                data=payload,
            )

        data = res.json()

        if data.get("code") != "0000":
            raise RuntimeError(f"Giftishow API 실패: {data}")

        inner = data.get("result", {})
        if inner.get("code") != "0000":
            raise RuntimeError(f"Giftishow 발송 실패: {inner}")

        result = inner.get("result", {})
        logger.info(f"[GIFTISHOW SEND SUCCESS] tr_id={tr_id}, result={result}")

        return result

    async def cancel_giftishow_coupon(self, tr_id: str, user_id: str):
        payload = {
            "api_code": "0202",
            "custom_auth_code": CUSTOM_AUTH_CODE,
            "custom_auth_token": CUSTOM_AUTH_TOKEN,
            "dev_yn": "N",
            "tr_id": tr_id,
            "user_id": "ask@couplematch.co.kr",
        }

        async with httpx.AsyncClient(timeout=15) as client:
            return await client.post(
                "https://bizapi.giftishow.com/bizApi/cancel",
                data=payload,
            )
        data = response.json()
        if data.get("code") not in ("0000", "0201"):
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "기프티콘 취소 실패",
                    "giftishow_response": data,
                },
            )
