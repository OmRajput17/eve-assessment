from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Payment, PaymentStatus, WebhookEvent
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository):
    def add(self, payment: Payment) -> Payment:
        self.db.add(payment)
        self.db.flush()
        return payment

    def get_by_reference(self, reference: str, *, lock: bool = False) -> Payment | None:
        stmt = select(Payment).where(Payment.provider_reference == reference)
        if lock:
            stmt = stmt.with_for_update(of=Payment)
        return self.db.scalars(stmt).first()

    def has_pending_for_booking(self, booking_id: int) -> bool:
        stmt = select(Payment.id).where(
            Payment.booking_id == booking_id, Payment.status == PaymentStatus.PENDING
        )
        return self.db.scalars(stmt).first() is not None


class WebhookEventRepository(BaseRepository):
    def register(self, event: WebhookEvent) -> bool:
        """Try to record the event. Returns False if this event_id was already seen.

        The UNIQUE(event_id) constraint makes this race-safe: even if two identical
        webhooks arrive at the exact same moment, only one INSERT can succeed.
        """
        try:
            self.db.add(event)
            self.db.flush()
            return True
        except IntegrityError:
            self.db.rollback()
            return False