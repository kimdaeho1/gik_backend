from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from fastapi import Form
from typing import Any, Dict


class GifticonProductResponse(BaseModel):
    goodsCode: str
    brandName: str
    goodsName: str
    content: str
    imageUrl: str
    imageThumbUrl: str
    priceReal: int
    priceSupply: int
    goodsState: str
    isActive: bool
    limitDays: int
    validEndDate: datetime
    coinPrice: int


class GifticonDetailResponse(BaseModel):
    mdCode: str
    discountPrice: int
    mmsGoodsImg: str
    limitDay: int
    content: str
    goodsDescImgWeb: str
    goodsImgB: str
    goodsTypeNm: str
    categoryName1: str
    goodsName: str
    mmsReserveFlag: str
    goodsStateCd: str
    brandCode: str
    goodsNo: int
    brandName: str
    brandIconImg: str
    goodsTypeCd: str
    saleDateFlagCd: str
    contentAddDesc: str
    categorySeq1: int
    goodsCode: str
    goodsTypeDtlNm: str
    goodsImgS: str
    affiliate: str
    saleDateFlag: str
    realPrice: int
    coinPrice: int
