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
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid authentication scheme.",
                )
            if not verify_token(credentials.credentials):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid or expired token.",
                )
            return credentials.credentials
        else:
            return None

    def verify_jwt(self, jwt_token: str) -> bool:
        try:
            payload = verify_token(jwt_token)
            return False if payload is None else True
        except Exception as e:
            return False


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
        user_id = payload.get("user_id")
        return user_id
    except ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None


# TODO: access_token, refresh_token만 하면 되는거 아님? user_id, expires_in이 필요한건가?
def create_new_tokens_based_on_refresh_token(refresh_token: str) -> Optional[dict]:
    user_id = verify_token(refresh_token)
    if user_id:
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

    return verify_token(token)
