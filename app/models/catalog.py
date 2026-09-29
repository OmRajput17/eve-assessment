from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

class DiagnosticCentre(TimestampMixin, Base):
    __tablename__ = "diagnostic_centres"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    location: Mapped[str] = mapped_column(String(150), index=True)

    offerings: Mapped[list["CentreTest"]] = relationship(
        back_populates="centre", cascade="all, delete-orphan"
    )


class DiagnosticTest(TimestampMixin, Base):
    """Catalogue entry, e.g. 'CBC' or 'Lipid Profile'. Price is NOT here (it varies per centre)."""

    __tablename__ = "diagnostic_tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    description: Mapped[str | None] = mapped_column(Text)


class CentreTest(TimestampMixin, Base):
    """Join table: which centre offers which test, and at what price."""

    __tablename__ = "centre_tests"
    __table_args__ = (
        UniqueConstraint("centre_id", "test_id", name="uq_centre_test"),
        CheckConstraint("price > 0", name="ck_centre_test_price_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    centre_id: Mapped[int] = mapped_column(ForeignKey("diagnostic_centres.id", ondelete="CASCADE"))
    test_id: Mapped[int] = mapped_column(ForeignKey("diagnostic_tests.id"))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    centre: Mapped[DiagnosticCentre] = relationship(back_populates="offerings")
    test: Mapped[DiagnosticTest] = relationship(lazy="joined")