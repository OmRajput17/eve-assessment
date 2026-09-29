from fastapi import APIRouter, Depends, status

from app.api.deps import get_booking_service, get_current_user
from app.models import User
from app.schemas.booking import BookingCreate, BookingOut
from app.schemas.common import Pagination
from app.services.booking import BookingService

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("/", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(
    data: BookingCreate,
    user: User = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service),
):
    return service.create(user, data)


@router.get("/", response_model=list[BookingOut])
def list_my_bookings(
    page: Pagination = Depends(),
    user: User = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service),
):
    return service.list_for_user(user, limit=page.limit, offset=page.offset)


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(
    booking_id: int,
    user: User = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service),
):
    return service.get_for_user(user, booking_id)


@router.post("/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(
    booking_id: int,
    user: User = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service),
):
    return service.cancel(user, booking_id)