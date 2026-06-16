import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.exceptions import AppError

logger = structlog.get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning("app_error", error_code=exc.error_code, message=exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.error_code, "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning("validation_error", errors=exc.errors())
        return JSONResponse(
            status_code=422,
            content={
                "error": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"errors": exc.errors()},
            },
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.error("db_integrity_error", error=str(exc.orig))
        return JSONResponse(
            status_code=409,
            content={
                "error": "CONFLICT",
                "message": "Database constraint violation",
                "details": {},
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": {},
            },
        )
