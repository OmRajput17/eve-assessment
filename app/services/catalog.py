from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models import CentreTest, DiagnosticCentre, DiagnosticTest
from app.repositories.catalog import CatalogRepository
from app.schemas.catalog import CentreCreate, OfferingCreate, TestCreate


class CatalogService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = CatalogRepository(db)

    def list_centres(self, *, location: str | None, limit: int, offset: int):
        return self._repo.list_centres(location=location, limit=limit, offset=offset)

    def get_centre(self, centre_id: int) -> DiagnosticCentre:
        centre = self._repo.get_centre(centre_id)
        if centre is None:
            raise NotFoundError("Centre not found")
        return centre

    def create_centre(self, data: CentreCreate) -> DiagnosticCentre:
        centre = self._repo.add_centre(DiagnosticCentre(name=data.name, location=data.location))
        self._db.commit()
        return self.get_centre(centre.id)

    def list_tests(self, *, limit: int, offset: int):
        return self._repo.list_tests(limit=limit, offset=offset)

    def create_test(self, data: TestCreate) -> DiagnosticTest:
        if self._repo.get_test_by_name(data.name):
            raise ConflictError("A test with this name already exists")
        test = self._repo.add_test(DiagnosticTest(name=data.name, description=data.description))
        self._db.commit()
        return test

    def add_offering(self, centre_id: int, data: OfferingCreate) -> DiagnosticCentre:
        if self._repo.get_centre(centre_id) is None:
            raise NotFoundError("Centre not found")
        if self._repo.get_test(data.test_id) is None:
            raise NotFoundError("Test not found")
        if self._repo.get_offering(centre_id, data.test_id):
            raise ConflictError("This centre already offers that test")

        self._repo.add_offering(
            CentreTest(centre_id=centre_id, test_id=data.test_id, price=data.price)
        )
        self._db.commit()
        self._db.expire_all()  # reload relationships for the response
        return self.get_centre(centre_id)