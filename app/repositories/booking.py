from sqlalchemy import select

from app.models import Booking
from app.repositories.base import BaseRepository


class BookingRepository(BaseRepository):
    def add(self, booking: Booking) -> Booking:
        self.db.add(booking)
        self.db.flush()
        return booking

    def get(self, booking_id: int, *, lock: bool = False) -> Booking | None:
        stmt = select(Booking).where(Booking.id == booking_id)
        if lock:
            stmt = stmt.with_for_update()  # SELECT ... FOR UPDATE (row lock)
        return self.db.scalars(stmt).first()

    def get_owned(self, booking_id: int, user_id: int, *, lock: bool = False) -> Booking | None:
        """Scoped by owner: someone else's booking looks exactly like a missing one."""
        stmt = select(Booking).where(Booking.id == booking_id, Booking.user_id == user_id)
        if lock:
            stmt = stmt.with_for_update()
        return self.db.scalars(stmt).first()

    def list_for_user(self, user_id: int, *, limit: int, offset: int) -> list[Booking]:
        stmt = (
            select(Booking)
            .where(Booking.user_id == user_id)
            .order_by(Booking.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(stmt))