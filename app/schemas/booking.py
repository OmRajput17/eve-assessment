from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import BookingStatus
from app.schemas.common import ORMModel


class BookingCreate(BaseModel):
    centre_id: int = Field(gt=0)
    test_id: int = Field(gt=0)
    appointment_at: datetime  # must include a timezone offset, e.g. 2030-01-15T10:00:00Z


class BookingOut(ORMModel):
    id: int
    user_id: int
    centre_id: int
    test_id: int
    appointment_at: datetime
    amount: Decimal
    status: BookingStatus
    created_at: datetime