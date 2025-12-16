from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, ExpiredSignatureError

from app.utils.config import SECRET_KEY, ALGORITHM

ACCESS_TOKEN_EXPIRE_DAYS = 1  # 액세스 토큰 유효 기간 (1일)
REFRESH_TOKEN_EXPIRE_DAYS = 30  # 리프레시 토큰 유효 기간 (30일)


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = False):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(
            JWTBearer, self
        ).__call__(request)

        if credentials:
            if credentials.scheme != "Bearer":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid authentication scheme.",
                )

            payload = verify_token(credentials.credentials)

            if not payload:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid or expired token.",
                )

            if not payload.get("user_id") and not payload.get("biz_id"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid token payload.",
                )

            return credentials.credentials
        else:
            return None


def create_token(user_id: str, expires_delta: timedelta) -> str:
    expire_dt = datetime.utcnow() + expires_delta
    encoded_jwt = jwt.encode(
        {"user_id": user_id, "exp": expire_dt}, SECRET_KEY, algorithm=ALGORITHM
    )
    return encoded_jwt


def create_access_token(user_id: str) -> str:
    return create_token(user_id, timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))


def create_refresh_token(user_id: str) -> str:
    return create_token(user_id, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))


def verify_token(token: str) -> Optional[str]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        return payload
    except ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None


# TODO: access_token, refresh_token만 하면 되는거 아님? user_id, expires_in이 필요한건가?
def create_new_tokens_based_on_refresh_token(refresh_token: str) -> Optional[dict]:
    payload = verify_token(refresh_token)
    if payload:
        user_id = payload.get("user_id")
        if not user_id:
            return None

        return {
            "user_id": user_id,
            "access_token": create_access_token(user_id),
            "refresh_token": create_refresh_token(user_id),
        }
    else:
        return None


# raise에러가 나면 return None은 의미가 없고, 그렇기 때문에 str.
async def get_user_id_from_token(token: str) -> str:
    if not token:
        return None
    payload = verify_token(token)
    if not payload:
        return None

    return payload.get("user_id")


# 비즈 전용 토큰 생성 및 검증 함수들
def create_access_token_biz(biz_id: str) -> str:
    expire_dt = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    encoded_jwt = jwt.encode(
        {"biz_id": biz_id, "exp": expire_dt}, SECRET_KEY, algorithm=ALGORITHM
    )
    return encoded_jwt


def create_refresh_token_biz(biz_id: str) -> str:
    expire_dt = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    encoded_jwt = jwt.encode(
        {"biz_id": biz_id, "exp": expire_dt}, SECRET_KEY, algorithm=ALGORITHM
    )
    return encoded_jwt


def get_biz_id_from_token(token: str) -> Optional[str]:
    if not token:
        return None

    try:
        payload = verify_token(token)
        return payload.get("biz_id")
    except ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None
