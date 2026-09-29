from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import CentreTest, DiagnosticCentre, DiagnosticTest
from app.repositories.base import BaseRepository


class CatalogRepository(BaseRepository):
    # ---- centres ----
    def list_centres(
        self, *, location: str | None, limit: int, offset: int
    ) -> list[DiagnosticCentre]:
        stmt = (
            select(DiagnosticCentre)
            .options(selectinload(DiagnosticCentre.offerings))  # avoids N+1 queries
            .order_by(DiagnosticCentre.id)
            .limit(limit)
            .offset(offset)
        )
        if location:
            stmt = stmt.where(DiagnosticCentre.location.ilike(f"%{location}%"))
        return list(self.db.scalars(stmt))

    def get_centre(self, centre_id: int) -> DiagnosticCentre | None:
        stmt = (
            select(DiagnosticCentre)
            .options(selectinload(DiagnosticCentre.offerings))
            .where(DiagnosticCentre.id == centre_id)
        )
        return self.db.scalars(stmt).first()

    def add_centre(self, centre: DiagnosticCentre) -> DiagnosticCentre:
        self.db.add(centre)
        self.db.flush()
        return centre

    # ---- tests ----
    def list_tests(self, *, limit: int, offset: int) -> list[DiagnosticTest]:
        stmt = select(DiagnosticTest).order_by(DiagnosticTest.id).limit(limit).offset(offset)
        return list(self.db.scalars(stmt))

    def get_test(self, test_id: int) -> DiagnosticTest | None:
        return self.db.get(DiagnosticTest, test_id)

    def get_test_by_name(self, name: str) -> DiagnosticTest | None:
        return self.db.scalars(select(DiagnosticTest).where(DiagnosticTest.name == name)).first()

    def add_test(self, test: DiagnosticTest) -> DiagnosticTest:
        self.db.add(test)
        self.db.flush()
        return test

    # ---- offerings ----
    def get_offering(self, centre_id: int, test_id: int) -> CentreTest | None:
        stmt = select(CentreTest).where(
            CentreTest.centre_id == centre_id, CentreTest.test_id == test_id
        )
        return self.db.scalars(stmt).first()

    def add_offering(self, offering: CentreTest) -> CentreTest:
        self.db.add(offering)
        self.db.flush()
        return offering