from app.db.db_connection import db
from aiomysql import Cursor
from app.db.credit import CreditHistory


class CreditManager:
    def __init__(self, user_id: str):
        self.db = db
        self.user_id = user_id

    async def get_credit_balance(self, cur: Cursor = None):
        """사용자의 현재 크레딧 잔액을 조회"""
        if cur is None:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    return await self._fetch_credit(cur)
        else:
            return await self._fetch_credit(cur)

    async def _fetch_credit(self, cur: Cursor):
        query = """
            SELECT credit 
            FROM users 
            WHERE user_id = %s
        """
        await cur.execute(query, (self.user_id,))
        result = await cur.fetchone()
        return result[0] if result else 0

    async def get_credit_history(self, cur: Cursor = None):
        """사용자의 크레딧 히스토리 조회"""
        if cur is None:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    credit_history = await self._fetch_credit_history(cur)
        else:
            credit_history = await self._fetch_credit_history(cur)

        credit_history = [
            CreditHistory(**dict(zip([col[0] for col in cur.description], row)))
            for row in credit_history
        ]

        return {"credit_history": [record.dict() for record in credit_history]}

    async def _fetch_credit_history(self, cur: Cursor):
        query = """
            SELECT 
                amount
                , description
                , reg_dt
            FROM credit_history 
            WHERE 
                user_id = %s
                and use_yn = 'Y'
            ORDER BY reg_dt DESC
        """
        await cur.execute(query, (self.user_id,))
        result = await cur.fetchall()
        return result

    async def change_credit(
        self, amount: int, description: str, increase=True, cur: Cursor = None
    ):
        """지정된 양만큼 크레딧을 증가시키거나 감소시킴"""
        if amount < 0:
            raise ValueError("크레딧 변경량은 음수가 될 수 없습니다.")

        if cur is None:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    return await self._change_credit_logic(
                        amount, description, increase, cur
                    )
        else:
            return await self._change_credit_logic(amount, description, increase, cur)

    async def _change_credit_logic(
        self, amount: int, description: str, increase: bool, cur: Cursor
    ):
        if not increase:  # 크레딧을 감소시키는 경우
            current_credit = await self.get_credit_balance(cur)
            if current_credit < amount:
                raise ValueError("보유 크레딧이 부족하여 차감할 수 없습니다.")

        credit_op = "+" if increase else "-"
        query = f"""
        UPDATE users
        SET credit = credit {credit_op} %s
        WHERE user_id = %s
        """
        await cur.execute(query, (amount, self.user_id))

        # 크레딧 히스토리 기록
        await self._insert_credit_history(amount, increase, description, cur)

    async def _insert_credit_history(
        self, amount: int, increase: bool, description: str, cur: Cursor
    ):
        if not increase:
            amount = -amount

        query = """
        INSERT INTO credit_history(user_id, amount, description)
        VALUES(%s, %s, %s)
        """
        await cur.execute(query, (self.user_id, amount, description))
