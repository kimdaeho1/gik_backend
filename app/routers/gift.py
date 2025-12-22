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
    brand_name: str = Query(None),
    service: GiftService = Depends(Provide[Container.gift_service]),
):
    goods_list = await service.get_gifticon_goods(page=page, brand_name=brand_name)
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
        "brandList": brand_list,
    }


@router.post("/gift/goods/cancel")
async def cancel_gifticon_after_send(
    tr_id: str,
    user_id: str,
):
    """
    테스트용 기프티콘 취소 API
    - 발송 성공
    - 메시지 수신 확인
    - 수동 취소
    """

    payload = {
        "api_code": "0202",
        "custom_auth_code": CUSTOM_AUTH_CODE,
        "custom_auth_token": CUSTOM_AUTH_TOKEN,
        "dev_yn": "N",  # 실 발송 테스트
        "tr_id": tr_id,
        "user_id": user_id,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            "https://bizapi.giftishow.com/bizApi/cancel",
            json=payload,
        )

    data = response.json()

    # Giftishow는 이미 취소된 경우도 응답이 다를 수 있음
    if data.get("code") not in ("0000", "0201"):
        # 0201: 이미 취소됨 (케이스에 따라 다를 수 있음)
        raise HTTPException(
            status_code=400,
            detail={
                "message": "기프티콘 취소 실패",
                "giftishow_response": data,
            },
        )

    return {
        "success": True,
        "message": "기프티콘 취소 완료",
        "giftishow_response": data,
    }


@router.post("/bizmoney")
async def get_bizmoney_balance(
    user_id: str,
):
    """
    비즈머니 잔액 조회 API
    - 발송 전 잔액 체크
    - 백오피스/운영자용
    """

    payload = {
        "api_code": "0301",
        "custom_auth_code": CUSTOM_AUTH_CODE,
        "custom_auth_token": CUSTOM_AUTH_TOKEN,
        "dev_yn": "N",
        "user_id": user_id,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            "https://bizapi.giftishow.com/bizApi/bizmoney",
            json=payload,
        )

    data = response.json()

    if data.get("code") != "0000":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "비즈머니 잔액 조회 실패",
                "giftishow_response": data,
            },
        )

    return {
        "success": True,
        "balance": int(data.get("balance", 0)),
        "giftishow_response": data,
    }
