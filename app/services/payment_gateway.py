import random
import uuid
from typing import Protocol

from app.models import PaymentStatus


class PaymentGateway(Protocol):
    """What PaymentService needs from ANY provider. Swap in Razorpay/Stripe by implementing this."""

    def new_reference(self) -> str: ...

    def charge(self, *, force: PaymentStatus | None = None) -> PaymentStatus: ...


class SimulatedPaymentGateway:
    """Fake provider: succeeds with probability `success_rate`."""

    def __init__(self, success_rate: float = 0.8, rng: random.Random | None = None) -> None:
        self._success_rate = success_rate
        self._rng = rng or random.Random()

    def new_reference(self) -> str:
        return f"sim_{uuid.uuid4().hex}"

    def charge(self, *, force: PaymentStatus | None = None) -> PaymentStatus:
        if force is not None:
            return force
        ok = self._rng.random() < self._success_rate
        return PaymentStatus.SUCCESS if ok else PaymentStatus.FAILED