import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import app.models
from app.api.routes import auth, bookings, catalog, payments
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    Base.metadata.create_all(bind=engine)  # fine for the assignment; use Alembic in production
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Diagnostic Booking & Payments API",
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    for module in (auth, catalog, bookings, payments):
        app.include_router(module.router)
    return app


app = create_app()