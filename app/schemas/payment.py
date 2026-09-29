from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import BookingStatus, PaymentStatus
from app.schemas.common import ORMModel

SettledStatus = Literal[PaymentStatus.SUCCESS, PaymentStatus.FAILED]


class PaymentCreate(BaseModel):
    booking_id: int = Field(gt=0)
    # async_mode=True leaves the payment PENDING until the webhook arrives.
    async_mode: bool = False
    # Dev/test only: force the simulated outcome.
    force_status: SettledStatus | None = None


class PaymentOut(ORMModel):
    id: int
    booking_id: int
    amount: Decimal
    status: PaymentStatus
    provider_reference: str
    booking_status: BookingStatus


class WebhookPayload(BaseModel):
    event_id: str = Field(min_length=1, max_length=100)
    provider_reference: str = Field(min_length=1, max_length=64)
    status: SettledStatus


class WebhookOutcome(str, Enum):
    PROCESSED = "processed"
    DUPLICATE = "duplicate"
    IGNORED = "ignored"


class WebhookResponse(BaseModel):
    outcome: WebhookOutcome