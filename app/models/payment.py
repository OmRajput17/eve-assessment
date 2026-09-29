from decimal import Decimal

from sqlalchemy import JSON, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.booking import Booking
from app.models.enums import BookingStatus, PaymentStatus


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False, length=20), default=PaymentStatus.PENDING
    )
    # The provider's id for this payment; webhooks reference it.
    provider_reference: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    booking: Mapped[Booking] = relationship(lazy="joined")

    @property
    def booking_status(self) -> BookingStatus:
        return self.booking.status

    @property
    def is_settled(self) -> bool:
        return self.status != PaymentStatus.PENDING


class WebhookEvent(TimestampMixin, Base):
    """Ledger of processed webhook events. UNIQUE(event_id) is the idempotency guard."""

    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    provider_reference: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)