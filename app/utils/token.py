from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status
from jose import jwt, ExpiredSignatureError 

from app.utils.config import SECRET_KEY, ALGORITHM

ACCESS_TOKEN_EXPIRE_DAYS = 1        # 액세스 토큰 유효 기간 (1일)
REFRESH_TOKEN_EXPIRE_DAYS = 30      # 리프레시 토큰 유효 기간 (30일)

def create_token(user_id: str, expires_delta: timedelta) -> str:
    expire_dt = datetime.utcnow() + expires_delta
    encoded_jwt = jwt.encode({"user_id": user_id, "exp": expire_dt}, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_access_token(user_id: str) -> str:
    return create_token(user_id, timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))
    

def create_refresh_token(user_id: str) -> str:
    return create_token(user_id, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))


def verify_token(token: str) -> Optional[str]:
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
    user_id = verify_token(token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")

    return user_id
