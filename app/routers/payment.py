import os
import time
import uuid
from datetime import datetime
from functools import lru_cache

import requests
from cryptography.x509 import load_pem_x509_certificate
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from googleapiclient.discovery import build
from httplib2 import Http
from jose import jwt
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

from app.db.payments.payments import PaymentsService
from app.schemas.payments import VerifyPaymentsAndroid, VerifyPaymentsIOS, Receipt
from app.utils.auth import get_user_no_from_token
from app.utils.logging_config import get_logger
from app.utils.config import (
    IOS_BUNDLE_ID,
    IOS_ISSUER_ID,
    IOS_KEY_ID,
    IOS_API_PRIVATE_KEY,
)


router = APIRouter()
logger = get_logger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

CREDENTIAL_FILE_PATH = os.getenv("GOOGLE_API_KEY_LOCAL_PATH", "/tmp/credential.json")


@lru_cache()
def get_android_publisher():
    """Google API 클라이언트를 반환합니다."""
    credential = ServiceAccountCredentials.from_json_keyfile_name(
        filename=CREDENTIAL_FILE_PATH,
        scopes=["https://www.googleapis.com/auth/androidpublisher"],
    )
    http_auth = credential.authorize(Http())
    return build("androidpublisher", "v3", http=http_auth)


def get_purchase_details(product_id, package_name, purchase_token):
    """구매 내역을 확인합니다."""
    client = get_android_publisher()
    return (
        client.purchases()
        .products()
        .get(productId=product_id, packageName=package_name, token=purchase_token)
        .execute()
    )


def get_product_price(product_id, package_name):
    """상품 가격 정보를 가져옵니다."""
    client = get_android_publisher()
    product_info = (
        client.inappproducts().get(packageName=package_name, sku=product_id).execute()
    )
    default_price = product_info.get("defaultPrice", {})
    price_micros = int(default_price.get("priceMicros", 0))
    currency_code = default_price.get("currency", "KRW")

    if price_micros > 0:
        return price_micros / 1_000_000, currency_code
    else:
        return None, None


@router.post("/v1/match/purchase/verify-android", status_code=status.HTTP_200_OK)
async def android_verify_purchase_endpoint(
    payments_info: VerifyPaymentsAndroid, token: str = Depends(oauth2_scheme)
):
    user_no = await get_user_no_from_token(token)

    try:
        # 구매 세부정보 가져오기
        try:
            purchase_details = get_purchase_details(
                payments_info.product_id,
                payments_info.package_name,
                payments_info.purchase_token,
            )
        except Exception as e:
            logger.error(f"구매 세부정보를 가져오는 중 오류 발생: {e}")
            raise HTTPException(
                status_code=500, detail="구매 세부정보를 확인할 수 없습니다."
            )

        # 상품 가격 정보 가져오기
        try:
            price, currency = get_product_price(
                payments_info.product_id, payments_info.package_name
            )
        except Exception as e:
            logger.error(f"상품 가격 정보를 가져오는 중 오류 발생: {e}")
            raise HTTPException(
                status_code=500, detail="상품 가격 정보를 확인할 수 없습니다."
            )

        if not price or not currency:
            logger.warning(f"가격 정보 누락: product_id={payments_info.product_id}")
            raise HTTPException(status_code=404, detail="가격 정보를 찾을 수 없습니다.")

        # Unix timestamp 변환
        purchase_time_millis = purchase_details.get("purchaseTimeMillis")
        if purchase_time_millis:
            utc_dt = datetime.fromtimestamp(
                int(purchase_time_millis) / 1000
            )  # UTC 시간
            kst_dt = utc_dt + timedelta(hours=9)  # UTC + 9시간 = KST
            purchase_dt = kst_dt.strftime("%Y-%m-%d %H:%M:%S")  # KST로 포맷팅
        else:
            purchase_dt = None

        receipt = Receipt(
            payment_source="ANDROID_INAPP",
            product_id=payments_info.product_id,
            package_name=payments_info.package_name,
            purchase_token=payments_info.purchase_token,
            order_id=purchase_details.get("orderId", ""),
            purchase_state=purchase_details.get("purchaseState"),
            acknowledgement_state=purchase_details.get("acknowledgementState"),
            consumption_state=purchase_details.get("consumptionState"),
            purchase_dt=purchase_dt,
            region_code=purchase_details.get("regionCode"),
            price=price,
            currency=currency,
            quantity=1,
        )

        payments_service = PaymentsService()
        if receipt.purchase_state == 0:
            is_success = await payments_service.purchase(user_no, receipt)
            if not is_success:
                logger.error(
                    f"구매 처리 실패: user_no={user_no}, order_id={receipt.order_id}"
                )
                raise HTTPException(
                    status_code=500, detail="구매 처리 중 오류가 발생했습니다."
                )
            logger.info(
                f"구매 검증 완료: user_no={user_no}, order_id={receipt.order_id}"
            )
            return {"is_success": True, "detail": "구매가 완료되었습니다."}

        elif receipt.purchase_state == 1:
            is_success = await payments_service.refund(user_no, receipt)
            if not is_success:
                logger.error(
                    f"환불 처리 실패: user_no={user_no}, order_id={receipt.order_id}"
                )
                raise HTTPException(
                    status_code=500, detail="환불 처리 중 오류가 발생했습니다."
                )
            logger.info(
                f"환불 처리 완료: user_no={user_no}, order_id={receipt.order_id}"
            )
            return {"is_success": True, "detail": "환불이 완료되었습니다."}
        else:
            logger.warning(
                f"예외적인 구매 상태: purchase_state={receipt.purchase_state}, user_no={user_no}"
            )
            return {
                "is_success": False,
                "detail": f"구매 상태가 유효하지 않습니다: {receipt.purchase_state}",
            }

    except Exception as e:
        logger.error(f"영수증 검증 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="영수증 검증 중 오류 발생")


@router.post("/v1/match/purchase/verify-ios", status_code=status.HTTP_200_OK)
async def ios_verify_purchase_endpoint(
    payments_info: VerifyPaymentsIOS, token: str = Depends(oauth2_scheme)
):
    user_no = await get_user_no_from_token(token)

    issue_time = round(time.time())
    expiration_time = issue_time + 60 * 60  # 1 hour expiration
    header = {"alg": "ES256", "kid": IOS_KEY_ID, "typ": "JWT"}
    payload = {
        "iss": IOS_ISSUER_ID,
        "iat": issue_time,
        "exp": expiration_time,
        "aud": "appstoreconnect-v1",
        "nonce": str(uuid.uuid4()),
        "bid": IOS_BUNDLE_ID,
    }

    jwt_token = jwt.encode(
        claims=payload, key=IOS_API_PRIVATE_KEY, headers=header, algorithm="ES256"
    )

    def _decode_jws(_encoded_jws: str):
        _header = jwt.get_unverified_header(_encoded_jws)

        _cert_str = f"-----BEGIN CERTIFICATE-----{_header['x5c'][0]}-----END CERTIFICATE-----".encode()
        _cert_obj = load_pem_x509_certificate(_cert_str)
        _public_key = _cert_obj.public_key()

        decoded_jws = jwt.decode(
            _encoded_jws,
            key=_public_key,
            algorithms=[_header["alg"]],
            options={"verify_signature": True},
        )
        return decoded_jws

    try:
        try:
            response = requests.get(
                url=f"https://api.storekit.itunes.apple.com/inApps/v1/transactions/{payments_info.transaction_id}",
                headers={"Authorization": f"Bearer {jwt_token}"},
            )

            if response.status_code == 200:
                response_data = response.json()
                signed_transaction_info = response_data.get("signedTransactionInfo")

                if not signed_transaction_info:
                    logger.error("signedTransactionInfo를 확인할 수 없습니다.")
                    raise HTTPException(
                        status_code=500,
                        detail="signedTransactionInfo를 확인할 수 없습니다.",
                    )

                # signedTransactionInfo 디코딩
                decoded_info = _decode_jws(signed_transaction_info)

                # Unix timestamp 변환
                purchase_time_millis = decoded_info.get("purchaseDate")
                if purchase_time_millis:
                    utc_dt = datetime.fromtimestamp(
                        int(purchase_time_millis) / 1000
                    )  # UTC 시간
                    kst_dt = utc_dt + timedelta(hours=9)  # UTC + 9시간 = KST
                    purchase_dt = kst_dt.strftime("%Y-%m-%d %H:%M:%S")  # KST로 포맷팅
                else:
                    purchase_dt = None

                # inAppOwnershipType 값 처리
                purchase_state = decoded_info.get(
                    "inAppOwnershipType", "UNKNOWN"
                )  # PURCHASED, FAMILY_SHARED 가능
                if purchase_state == "PURCHASED":
                    purchase_state = 0
                else:
                    purchase_state = 99

                if purchase_state == 0:
                    # Receipt 생성
                    receipt = Receipt(
                        payment_source="IOS_INAPP",
                        package_name=decoded_info.get("bundleId"),
                        product_id=decoded_info.get("productId"),
                        purchase_token=None,
                        order_id=decoded_info.get("transactionId"),
                        purchase_state=purchase_state,
                        acknowledgement_state=None,
                        consumption_state=None,
                        purchase_dt=purchase_dt,
                        region_code=decoded_info.get("storefront", ""),
                        price=decoded_info.get("price", 0) / 1000,
                        currency=decoded_info.get("currency", "KRW"),
                        quantity=decoded_info.get("quantity", 0),
                    )

                    payments_service = PaymentsService()
                    is_success = await payments_service.purchase(user_no, receipt)

                    if not is_success:
                        logger.error(
                            f"구매 처리 실패: user_no={user_no}, transaction_id={payments_info.transaction_id}"
                        )
                        raise HTTPException(
                            status_code=500, detail="구매 처리 중 오류가 발생했습니다."
                        )

                    logger.info(
                        f"IOS 구매 검증 완료: user_no={user_no}, transaction_id={payments_info.transaction_id}"
                    )
                    return {"is_success": True, "detail": "구매가 완료되었습니다."}
                else:
                    logger.warning(
                        f"예외적인 구매 상태: purchase_state={purchase_state}, user_no={user_no}"
                    )
                    return {
                        "is_success": False,
                        "detail": f"구매 상태가 유효하지 않습니다: {purchase_state}",
                    }
        except Exception as e:
            logger.error(f"구매 세부정보를 가져오는 중 오류 발생: {e}")
            raise HTTPException(
                status_code=500, detail="구매 세부정보를 확인할 수 없습니다."
            )
    except Exception as e:
        logger.error(f"영수증 검증 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="영수증 검증 중 오류 발생")
