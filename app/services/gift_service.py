from app.db.db_connection import db
from app.repository.user_repository import UserRepository
from app.repository.gift_repository import GiftRepository
from app.db.gift import GifticonProductResponse, GifticonDetailResponse
from typing import List, Optional
import httpx, math
from app.utils.logging_config import get_logger
from app.utils.config import CUSTOM_AUTH_CODE, CUSTOM_AUTH_TOKEN
from app.utils.token import get_user_id_from_token
from datetime import datetime

logger = get_logger(__name__)


def generate_tr_id(user_id: str) -> str:
    return f"gift_{datetime.now():%Y%m%d%H%M%S}_{user_id[-6:]}"


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

    # async def purchase_gifticon_goods(self, token: str, goods_code: str):
    #     user_id = get_user_id_from_token(token=token)
    #     tr_id = generate_tr_id(user_id)

    #     async with self.db.get_connection() as conn:
    #         async with conn.cursor() as cur:
    #             try:
    #                 await conn.begin()

    #                 await cur.execute(
    #                     """
    #                     SELECT price_real
    #                     FROM gifticon_product
    #                     WHERE goods_code = %s
    #                       AND is_active = 1
    #                       AND goods_state = 'SALE'
    #                     """,
    #                     (goods_code,),
    #                 )
    #                 row = await cur.fetchone()
    #                 if not row:
    #                     raise HTTPException(404, "판매 중인 상품이 아닙니다.")

    #                 price_real = row[0]
    #                 price_credit = price_real // 50

    #                 await cur.execute(
    #                     """
    #                     SELECT pink_credit
    #                     FROM users
    #                     WHERE id = %s
    #                     FOR UPDATE
    #                     """,
    #                     (user_id,),
    #                 )
    #                 credit_row = await cur.fetchone()
    #                 if credit_row[0] < price_credit:
    #                     raise HTTPException(400, "크레딧 부족")

    #                 await cur.execute(
    #                     """
    #                     UPDATE users
    #                     SET pink_credit = pink_credit - %s
    #                     WHERE id = %s
    #                     """,
    #                     (price_credit, user_id),
    #                 )

    #                 await cur.execute(
    #                     """
    #                     INSERT INTO gifticon_purchase
    #                     (user_id, goods_code, tr_id, price_real, price_credit, status)
    #                     VALUES (%s, %s, %s, %s, %s, 'PENDING')
    #                     """,
    #                     (user_id, goods_code, tr_id, price_real, price_credit),
    #                 )

    #                 await conn.commit()

    #             except Exception:
    #                 await conn.rollback()
    #                 raise

    # async def send_giftishow_coupon(self, tr_id: str, user_id: str, goods_code: str):
    #     payload = {
    #         "api_code": "0204",
    #         "custom_auth_code": CUSTOM_AUTH_CODE,
    #         "custom_auth_token": CUSTOM_AUTH_TOKEN,
    #         "dev_yn": "N",
    #         "goods_code": goods_code,
    #         "mms_msg": "기프티콘이 도착했습니다.",
    #         "mms_title": "기프티콘",
    #         "callback_no": "01012345678",
    #         "phone_no": "01098765432",
    #         "tr_id": tr_id,
    #         "user_id": user_id,
    #         "gubun": "I",
    #     }

    #     async with httpx.AsyncClient(timeout=15) as client:
    #         return await client.post(
    #             "https://bizapi.giftishow.com/bizApi/send",
    #             data=payload,
    #         )

    # async def cancel_giftishow_coupon(self, tr_id: str, user_id: str):
    #     payload = {
    #         "api_code": "0202",
    #         "custom_auth_code": CUSTOM_AUTH_CODE,
    #         "custom_auth_token": CUSTOM_AUTH_TOKEN,
    #         "dev_yn": "N",
    #         "tr_id": tr_id,
    #         "user_id": user_id,
    #     }

    #     async with httpx.AsyncClient(timeout=15) as client:
    #         return await client.post(
    #             "https://bizapi.giftishow.com/bizApi/cancel",
    #             data=payload,
    #         )
