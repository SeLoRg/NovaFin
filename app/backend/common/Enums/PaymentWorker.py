from enum import Enum


class PaymentWorker(Enum):
    STRIPE = "stripe"
    CLOUDPAYMENTS = "cloudpayments"
