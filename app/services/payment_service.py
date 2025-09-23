from app.services.credit_service import CreditManager
from app.db.db_connection import db
from app.db.payment import SaleProduct, Receipt
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class PaymentsService:
    def __init__(self):
        self.db = db

    async def purchase(self, user_id: str, receipt: Receipt) -> bool:
        """
        구매 처리 로직
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await conn.begin()
                try:
                    # 중복 구매 확인
                    duplicate_check_query = """
                     SELECT EXISTS (
                         SELECT 1
                         FROM payments
                         WHERE order_id = %s
                     )
                     """
                    await cur.execute(duplicate_check_query, (receipt.order_id,))
                    is_duplicate = await cur.fetchone()
                    if is_duplicate[0]:
                        logger.warning(
                            f"중복 구매 시도: order_id={receipt.order_id}, user_id={user_id}"
                        )
                        return False

                    # 구매 정보 저장
                    insert_query = """
                    INSERT INTO payments (
                        user_id, payment_source, product_id, package_name, purchase_token, 
                        order_id, purchase_state, acknowledgement_state, 
                        consumption_state, purchase_dt, region_code, price, currency, quantity
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    await cur.execute(
                        insert_query,
                        (
                            user_id,
                            receipt.payment_source,
                            receipt.product_id,
                            receipt.package_name,
                            receipt.purchase_token,
                            receipt.order_id,
                            receipt.purchase_state,
                            receipt.acknowledgement_state,
                            receipt.consumption_state,
                            receipt.purchase_dt,
                            receipt.region_code,
                            receipt.price,
                            receipt.currency,
                            receipt.quantity,
                        ),
                    )

                    credit_manager = CreditManager(user_id)
                    credit_amount = getattr(SaleProduct, receipt.product_id, 0)
                    if credit_amount == 0:
                        logger.error(f"잘못된 product_id: {receipt.product_id}")
                        raise ValueError(f"잘못된 product_id: {receipt.product_id}")

                    await credit_manager.change_credit(
                        amount=int(credit_amount * receipt.quantity),
                        description="고래 구입",
                        increase=True,
                        cur=cur,
                    )

                    await conn.commit()
                    return True
                except Exception as e:
                    await conn.rollback()
                    logger.error(f"구매 처리 중 오류 발생: {e}")
                    return False

    async def refund(self, user_id: str, receipt: Receipt) -> bool:
        """
        환불 처리 로직
        """
        async with self.db.get_connection() as conn:
            async with conn.cursor() as cur:
                await conn.begin()
                try:
                    # 구매 이력이 있는지 확인 From user_purchases -> payments.
                    # user_purchases 테이블이 없음. payments가 맞는듯.
                    purchase_check_query = """
                    SELECT EXISTS (
                        SELECT 1
                        FROM payments
                        WHERE 
                            order_id = %s 
                            AND purchase_state = 0
                    )
                    """
                    await cur.execute(purchase_check_query, (receipt.order_id,))
                    is_purchase_exists = await cur.fetchone()
                    if not is_purchase_exists[0]:
                        logger.warning(
                            f"환불 요청 시 구매 이력 없음: order_id={receipt.order_id}, user_id={user_id}"
                        )
                        return False

                    # 다이아 회수
                    credit_manager = CreditManager(user_id)
                    whale_amount = getattr(SaleProduct, receipt.product_id, 0)
                    if whale_amount == 0:
                        raise ValueError(f"잘못된 product_id: {receipt.product_id}")

                    await credit_manager.change_credit(
                        amount=whale_amount,
                        description="고래 환불",
                        increase=False,
                        cur=cur,
                    )

                    # 구매 상태를 환불로 업데이트
                    update_query = """
                    UPDATE payments
                    SET purchase_state = 1
                    WHERE order_id = %s
                    """
                    await cur.execute(update_query, (receipt.order_id,))

                    await conn.commit()
                    return True
                except Exception as e:
                    await conn.rollback()
                    logger.error(f"환불 처리 중 오류 발생: {e}")
                    return False
