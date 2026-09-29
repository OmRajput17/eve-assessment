from fastapi import Query
from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class Pagination:
    """Reusable dependency: ?limit=20&offset=0"""

    def __init__(
        self,
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ) -> None:
        self.limit = limit
        self.offset = offset