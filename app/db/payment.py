from datetime import date
from pydantic import BaseModel


class SaleProduct:
    cm_whale_10 = 10
    cm_whale_30 = 30
    cm_whale_55 = 55
    cm_whale_120 = 120
    cm_whale_250 = 250
    cm_whale_700 = 700
    cm_whale_1500 = 1500


class VerifyPaymentsAndroid(BaseModel):
    product_id: str
    package_name: str
    purchase_token: str


class VerifyPaymentsIOS(BaseModel):
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
