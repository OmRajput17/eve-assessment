from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_catalog_service, require_admin
from app.schemas.catalog import (
    CentreCreate,
    CentreOut,
    OfferingCreate,
    TestCreate,
    TestOut,
)
from app.schemas.common import Pagination
from app.services.catalog import CatalogService

router = APIRouter(tags=["catalog"])


@router.get("/centres", response_model=list[CentreOut])
def list_centres(
    location: str | None = Query(default=None, max_length=150),
    page: Pagination = Depends(),
    service: CatalogService = Depends(get_catalog_service),
):
    return service.list_centres(location=location, limit=page.limit, offset=page.offset)


@router.get("/centres/{centre_id}", response_model=CentreOut)
def get_centre(centre_id: int, service: CatalogService = Depends(get_catalog_service)):
    return service.get_centre(centre_id)


@router.post(
    "/centres", response_model=CentreOut, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_centre(data: CentreCreate, service: CatalogService = Depends(get_catalog_service)):
    return service.create_centre(data)


@router.post(
    "/centres/{centre_id}/tests", response_model=CentreOut, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def add_centre_test(
    centre_id: int, data: OfferingCreate, service: CatalogService = Depends(get_catalog_service)
):
    return service.add_offering(centre_id, data)


@router.get("/tests", response_model=list[TestOut])
def list_tests(page: Pagination = Depends(), service: CatalogService = Depends(get_catalog_service)):
    return service.list_tests(limit=page.limit, offset=page.offset)


@router.post(
    "/tests", response_model=TestOut, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_test(data: TestCreate, service: CatalogService = Depends(get_catalog_service)):
    return service.create_test(data)