from app.db.db_connection import db
from jose import jwt, JWTError, ExpiredSignatureError
from app.utils.config import SECRET_KEY, ALGORITHM

class TokenService:
    def __init__(self):
        self.db = db
        
    async def generate_user_token(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str
    ):
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        UPDATE users
                        SET access_token = %s, refresh_token = %s
                        WHERE id = %s
                        """
                        , (access_token, refresh_token, user_id)
                    )              
                    await conn.commit()
                    return True
                
        # TODO: 추후 로깅을 추가해 어떤 에러가 발생했는지 확인할 수 있도록 개선
        except Exception as e:
            print(f"토큰 발급에 실패했습니다: {e}")
            return False
