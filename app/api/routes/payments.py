from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_payment_service, verify_webhook_signature
from app.models import User
from app.schemas.payment import PaymentCreate, PaymentOut, WebhookPayload, WebhookResponse
from app.services.payment import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(
    data: PaymentCreate,
    user: User = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
):
    return service.pay(user, data)


@router.post(
    "/webhook/",
    response_model=WebhookResponse,
    dependencies=[Depends(verify_webhook_signature)],
)
def payment_webhook(
    payload: WebhookPayload, service: PaymentService = Depends(get_payment_service)
):
    return WebhookResponse(outcome=service.handle_webhook(payload))