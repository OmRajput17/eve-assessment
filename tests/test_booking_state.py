import pytest

from app.core.exceptions import InvalidStateTransition
from app.models import Booking, BookingStatus


def make(status: BookingStatus) -> Booking:
    return Booking(status=status)


@pytest.mark.parametrize(
    "start,end",
    [
        (BookingStatus.PENDING, BookingStatus.CONFIRMED),
        (BookingStatus.PENDING, BookingStatus.FAILED),
        (BookingStatus.FAILED, BookingStatus.CONFIRMED),
        (BookingStatus.CONFIRMED, BookingStatus.CANCELLED),
    ],
)
def test_allowed_transitions(start, end):
    booking = make(start)
    booking.transition_to(end)
    assert booking.status == end


@pytest.mark.parametrize(
    "start,end",
    [
        (BookingStatus.CANCELLED, BookingStatus.CONFIRMED),
        (BookingStatus.CONFIRMED, BookingStatus.PENDING),
        (BookingStatus.CONFIRMED, BookingStatus.FAILED),
    ],
)
def test_forbidden_transitions(start, end):
    with pytest.raises(InvalidStateTransition):
        make(start).transition_to(end)