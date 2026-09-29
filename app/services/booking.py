from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import DomainValidationError, NotFoundError
from app.models import Booking, BookingStatus, User
from app.repositories.booking import BookingRepository
from app.repositories.catalog import CatalogRepository
from app.schemas.booking import BookingCreate


class BookingService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._bookings = BookingRepository(db)
        self._catalog = CatalogRepository(db)

    def create(self, user: User, data: BookingCreate) -> Booking:
        if data.appointment_at.tzinfo is None:
            raise DomainValidationError("appointment_at must include a timezone offset")
        if data.appointment_at <= datetime.now(UTC):
            raise DomainValidationError("appointment_at must be in the future")

        offering = self._catalog.get_offering(data.centre_id, data.test_id)
        if offering is None:
            raise NotFoundError("This centre does not offer the requested test")

        booking = Booking(
            user_id=user.id,
            centre_id=data.centre_id,
            test_id=data.test_id,
            appointment_at=data.appointment_at,
            amount=offering.price,  # price is decided by the server, never by the client
        )
        self._bookings.add(booking)
        self._db.commit()
        return booking

    def get_for_user(self, user: User, booking_id: int) -> Booking:
        booking = self._bookings.get_owned(booking_id, user.id)
        if booking is None:
            raise NotFoundError("Booking not found")
        return booking

    def list_for_user(self, user: User, *, limit: int, offset: int) -> list[Booking]:
        return self._bookings.list_for_user(user.id, limit=limit, offset=offset)

    def cancel(self, user: User, booking_id: int) -> Booking:
        booking = self._bookings.get_owned(booking_id, user.id, lock=True)
        if booking is None:
            raise NotFoundError("Booking not found")
        booking.transition_to(BookingStatus.CANCELLED)  # state machine decides if allowed
        self._db.commit()
        return booking