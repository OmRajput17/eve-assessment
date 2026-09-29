from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

class TestCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=1000)

class TestOut(ORMModel):
    id: int
    name: str
    description: str | None


class CentreCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    location: str = Field(min_length=2, max_length=150)


class OfferingCreate(BaseModel):
    test_id: int = Field(gt=0)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class OfferingOut(ORMModel):
    test: TestOut
    price: Decimal


class CentreOut(ORMModel):
    id: int
    name: str
    location: str
    offerings: list[OfferingOut]
