from datetime import date
from pydantic import BaseModel


class SaleProduct:
    gik_coin_10 = 10
    gik_coin_30 = 30
    gik_coin_55 = 55
    gik_coin_120 = 120
    gik_coin_250 = 250
    gik_coin_700 = 700
    gik_coin_1500 = 1500


class VerifyPaymentsAndroid(BaseModel):
    product_id: str
    package_name: str
    purchase_token: str


class VerifyPaymentsIOS(BaseModel):
    is_dev: bool
    transaction_id: str


class Receipt(BaseModel):
    payment_source: str
    product_id: str
    package_name: str | None
    purchase_token: str | None
    order_id: str | None
    purchase_state: int
    acknowledgement_state: int | None
    consumption_state: int | None
    purchase_dt: str
    region_code: str | None
    price: float
    currency: str
    quantity: int
