from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
import hashlib
import hmac

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User
from app.repositories.user import UserRepository
from app.services.auth import AuthService
from app.services.booking import BookingService
from app.services.catalog import CatalogService
from app.services.payment import PaymentService
from app.services.payment_gateway import PaymentGateway, SimulatedPaymentGateway

bearer_scheme = HTTPBearer(auto_error=False)


# ---- authentication / authorisation -------------------------------------
def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise UnauthorizedError("Missing bearer token")
    user_id = decode_access_token(creds.credentials)
    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise UnauthorizedError("User no longer exists")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise ForbiddenError("Admin access required")
    return user


# ---- webhook signature ----------------------------------------------------
async def verify_webhook_signature(
    request: Request, x_signature: str | None = Header(default=None)
) -> None:
    """HMAC-SHA256 of the raw body using a shared secret, like real providers do."""
    if not x_signature:
        raise UnauthorizedError("Missing X-Signature header")
    body = await request.body()
    expected = hmac.new(get_settings().webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, x_signature):  # constant-time compare
        raise UnauthorizedError("Invalid webhook signature")


# ---- service factories (dependency injection) ------------------------------
def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_catalog_service(db: Session = Depends(get_db)) -> CatalogService:
    return CatalogService(db)


def get_booking_service(db: Session = Depends(get_db)) -> BookingService:
    return BookingService(db)


def get_payment_gateway() -> PaymentGateway:
    return SimulatedPaymentGateway(success_rate=get_settings().payment_success_rate)


def get_payment_service(
    db: Session = Depends(get_db), gateway: PaymentGateway = Depends(get_payment_gateway)
) -> PaymentService:
    return PaymentService(db, gateway)