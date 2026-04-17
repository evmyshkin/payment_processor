from enum import Enum


class PaymentStatusEnum(Enum):
    PENDING = 'pending'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
