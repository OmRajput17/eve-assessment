import logging

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models import (
    Booking,
    BookingStatus,
    Payment,
    PaymentStatus,
    User,
    WebhookEvent,
)
from app.repositories.booking import BookingRepository
from app.repositories.payments import PaymentRepository, WebhookEventRepository
from app.schemas.payment import PaymentCreate, WebhookOutcome, WebhookPayload
from app.services.payment_gateway import PaymentGateway

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(
        self, db: Session, gateway: PaymentGateway, settings: Settings | None = None
    ) -> None:
        self._db = db
        self._gateway = gateway
        self._settings = settings or get_settings()
        self._bookings = BookingRepository(db)
        self._payments = PaymentRepository(db)
        self._events = WebhookEventRepository(db)

    # ------------------------------------------------------------------ pay
    def pay(self, user: User, data: PaymentCreate) -> Payment:
        if data.force_status and not self._settings.allow_payment_override:
            raise ForbiddenError("force_status is disabled in this environment")

        booking = self._bookings.get_owned(data.booking_id, user.id, lock=True)
        if booking is None:
            raise NotFoundError("Booking not found")
        if not booking.is_payable:
            raise ConflictError(f"Booking is {booking.status.value} and cannot be paid")
        if self._payments.has_pending_for_booking(booking.id):
            raise ConflictError("A payment for this booking is already in progress")

        payment = self._payments.add(
            Payment(
                booking_id=booking.id,
                amount=booking.amount,
                provider_reference=self._gateway.new_reference(),
            )
        )

        if not data.async_mode:
            result = self._gateway.charge(force=data.force_status)
            self._settle(payment, booking, result)

        self._db.commit()
        return payment

    # -------------------------------------------------------------- webhook
    def handle_webhook(self, payload: WebhookPayload) -> WebhookOutcome:
        """Idempotent. Safe to call any number of times with the same event."""
        event = WebhookEvent(
            event_id=payload.event_id,
            provider_reference=payload.provider_reference,
            payload=payload.model_dump(mode="json"),
        )
        # Step 1: claim the event id. A duplicate is acknowledged and does nothing.
        if not self._events.register(event):
            logger.info("webhook_duplicate", extra={"extra_fields": {"event_id": payload.event_id}})
            return WebhookOutcome.DUPLICATE

        # Step 2: find the payment. Unknown reference -> 404; rolling back un-claims
        # the event so the provider can legitimately retry later.
        payment = self._payments.get_by_reference(payload.provider_reference, lock=True)
        if payment is None:
            self._db.rollback()
            raise NotFoundError("Unknown provider_reference")

        # Step 3: apply only if the payment is still PENDING. Late or conflicting
        # events for an already-settled payment never overwrite the final state.
        if payment.is_settled:
            logger.warning(
                "webhook_ignored_already_settled",
                extra={"extra_fields": {"event_id": payload.event_id, "status": payment.status.value}},
            )
            outcome = WebhookOutcome.IGNORED
        else:
            booking = self._bookings.get(payment.booking_id, lock=True)
            self._settle(payment, booking, payload.status)
            outcome = WebhookOutcome.PROCESSED

        self._db.commit()  # event row + payment + booking change commit atomically
        return outcome

    # -------------------------------------------------------------- helpers
    def _settle(self, payment: Payment, booking: Booking, result: PaymentStatus) -> None:
        """Apply a final payment result to the payment and its booking."""
        payment.status = result

        if booking.is_cancelled:
            # Money moved on a booking the user already cancelled: keep the booking
            # CANCELLED and flag it (in real life: trigger a refund).
            logger.warning(
                "payment_on_cancelled_booking",
                extra={"extra_fields": {"booking_id": booking.id, "payment_id": payment.id}},
            )
            return

        target = BookingStatus.CONFIRMED if result == PaymentStatus.SUCCESS else BookingStatus.FAILED
        # A late FAILED must not downgrade an already CONFIRMED booking
        if booking.status == BookingStatus.CONFIRMED and target == BookingStatus.FAILED:
            return
        booking.transition_to(target)