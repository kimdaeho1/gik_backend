from app.db.db_connection import db
from app.repository.user_repository import UserRepository
from app.repository.gift_repository import GiftRepository
from app.db.gift import GifticonProductResponse, GifticonDetailResponse
from typing import List
import httpx, math
from app.utils.logging_config import get_logger
from app.utils.config import CUSTOM_AUTH_CODE, CUSTOM_AUTH_TOKEN
from app.utils.token import get_user_id_from_token

logger = get_logger(__name__)


class GiftService:
    def __init__(
        self,
        user_repository: UserRepository,
        gift_repository: GiftRepository,
    ):
        self.user_repository = user_repository
        self.gift_repository = gift_repository

    async def get_gifticon_goods(self, page: int) -> List[GifticonProductResponse]:
        goods_list = await self.gift_repository.get_gifticon_goods(page=page)

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

    async def get_gifticon_list_by_brand_name(
        self, brand_name: str
    ) -> List[GifticonProductResponse]:
        goods_list = await self.gift_repository.get_gifticon_list_by_brand_name(
            brand_name=brand_name
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

    async def purchase_gifticon_goods(
        self,
        token: str,
        goods_code: str,
    ):
        user_id = get_user_id_from_token(token=token)

    # async def cancel_gifticon_goods(
    #     self,
    #     token: str,
    #     tr_id: str,
    # ):
    #     user_id = get_user_id_from_token(token=token)
    #     try:
    #         async with
