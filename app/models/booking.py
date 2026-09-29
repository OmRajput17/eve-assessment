from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, ForeignKeyConstraint, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.core.exceptions import InvalidStateTransition
from app.db.base import Base, TimestampMixin
from app.models.enums import BookingStatus

_ALLOWED_TRANSITIONS: dict[BookingStatus, set[BookingStatus]] = {
    BookingStatus.PENDING: {BookingStatus.CONFIRMED, BookingStatus.FAILED, BookingStatus.CANCELLED},
    BookingStatus.FAILED: {BookingStatus.CONFIRMED, BookingStatus.CANCELLED},  # payment retry allowed
    BookingStatus.CONFIRMED: {BookingStatus.CANCELLED},
    BookingStatus.CANCELLED: set(),  # terminal
}

class Booking(TimestampMixin, Base):
    __tablename__ = "bookings"
    __table_args__ = (
        # Guarantees the (centre, test) pair really is an offering. DB-level integrity.
        ForeignKeyConstraint(
            ["centre_id", "test_id"],
            ["centre_tests.centre_id", "centre_tests.test_id"],
            name="fk_booking_offering",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    centre_id: Mapped[int] = mapped_column()
    test_id: Mapped[int] = mapped_column()
    appointment_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Snapshot of the price at booking time: later price changes must not alter old bookings.
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, native_enum=False, length=20), default=BookingStatus.PENDING, index=True
    )

    # ---- domain behaviour (encapsulation) ----
    def transition_to(self, new_status: BookingStatus) -> None:
        """The ONLY way to change status. Enforces the state machine."""
        if new_status == self.status:
            return
        if new_status not in _ALLOWED_TRANSITIONS[self.status]:
            raise InvalidStateTransition(
                f"Cannot move booking from {self.status.value} to {new_status.value}"
            )
        self.status = new_status

    @property
    def is_payable(self) -> bool:
        return self.status in (BookingStatus.PENDING, BookingStatus.FAILED)

    @property
    def is_cancelled(self) -> bool:
        return self.status == BookingStatus.CANCELLED