from fastapi import APIRouter, HTTPException, status, Depends, Query
import httpx
from dependency_injector.wiring import inject, Provide
from app.core.container import Container
from app.services.gift_service import GiftService
from app.utils.logging_config import get_logger
from app.utils.config import CUSTOM_AUTH_CODE, CUSTOM_AUTH_TOKEN
from app.utils.token import JWTBearer

oauth2_scheme = JWTBearer(auto_error=False)
logger = get_logger(__name__)

router = APIRouter(prefix="/v1/gik-backend/gift", tags=["Gift"])


@router.get("/goods/list")
@inject
async def get_gifticon_goods(
    page: int = Query(...),
    service: GiftService = Depends(Provide[Container.gift_service]),
):
    goods_list = await service.get_gifticon_goods(page=page)
    return {
        "success": True,
        "data": goods_list,
    }


@router.post("/goods/{goods_code}")
@inject
async def purchase_goods(
    goods_code: str,
    token: str = Depends(oauth2_scheme),
    service: GiftService = Depends(Provide[Container.gift_service]),
):
    result = await service.purchase_gifticon_goods(token=token, goods_code=goods_code)
    return {
        "success": True,
        "message": "기프티콘 구매에 성공했습니다.",
    }


@router.get("/goods/detail/{goods_code}")
@inject
async def get_goods_detail(
    goods_code: str,
    service: GiftService = Depends(Provide[Container.gift_service]),
):
    payload = {
        "api_code": "0111",
        "custom_auth_code": CUSTOM_AUTH_CODE,
        "custom_auth_token": CUSTOM_AUTH_TOKEN,
        "dev_yn": "N",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"https://bizapi.giftishow.com/bizApi/goods/{goods_code}",
                params=payload,
            )
    except Exception:
        raise HTTPException(status_code=502, detail="Giftishow API 연결 실패")

    try:
        data = response.json()
        goods_detail = await service.get_gifticon_goods_detail(
            data["result"]["goodsDetail"]
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Giftishow 응답 파싱 실패")
    return {
        "success": True,
        "data": goods_detail,
    }


@router.post("/goods/brand")
async def get_gifticon_brands():

    payload = {
        "api_code": "0102",
        "custom_auth_code": CUSTOM_AUTH_CODE,
        "custom_auth_token": CUSTOM_AUTH_TOKEN,
        "dev_yn": "N",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://bizapi.giftishow.com/bizApi/brands",
                params=payload,
            )
    except Exception:
        raise HTTPException(status_code=502, detail="Giftishow API 연결 실패")

    try:
        data = response.json()
    except Exception:
        raise HTTPException(status_code=502, detail="Giftishow 응답 파싱 실패")

    return {
        "success": True,
        "data": data["result"],
    }


@router.post("/goods/brand/{brand_code}")
async def get_gifticon_brands_detail(
    brand_code: str,
):
    payload = {
        "api_code": "0112",
        "custom_auth_code": CUSTOM_AUTH_CODE,
        "custom_auth_token": CUSTOM_AUTH_TOKEN,
        "dev_yn": "N",
        "brand_code": brand_code,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"https://bizapi.giftishow.com/bizApi/brands/{brand_code}",
                params=payload,
            )
    except Exception:
        raise HTTPException(status_code=502, detail="Giftishow API 연결 실패")

    try:
        data = response.json()
    except Exception:
        raise HTTPException(status_code=502, detail="Giftishow 응답 파싱 실패")

    return {
        "success": True,
        "data": data["result"],
    }


@router.get("/goods/brand/{brand_name}")
@inject
async def get_gifticon_list_by_brand_name(
    brand_name: str, service: GiftService = Depends(Provide[Container.gift_service])
):
    goods_list = await service.get_gifticon_list_by_brand_name(brand_name=brand_name)

    return {
        "success": True,
        "data": goods_list,
    }


@router.get("/goods/category")
@inject
async def get_goods_category_list(
    service: GiftService = Depends(Provide[Container.gift_service]),
):
    category_list = await service.gift_repository.get_goods_category_list()

    return {
        "success": True,
        "categoryList": category_list,
    }


@router.get("/goods/category/brand")
@inject
async def get_category_brand_list(
    category: str = Query(...),
    service: GiftService = Depends(Provide[Container.gift_service]),
):
    brand_list = await service.gift_repository.get_category_brand_list(
        category=category
    )

    return {
        "success": True,
        "bradnList": brand_list,
    }
