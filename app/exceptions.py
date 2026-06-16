from dataclasses import dataclass, field


@dataclass
class AppError(Exception):
    message: str
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    details: dict = field(default_factory=dict)  # type: ignore[type-arg]


class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: str | int) -> None:
        super().__init__(
            message=f"{resource} with id '{identifier}' not found",
            status_code=404,
            error_code="NOT_FOUND",
        )


class ConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=409, error_code="CONFLICT")


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message=message, status_code=401, error_code="UNAUTHORIZED")


class ForbiddenError(AppError):
    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message=message, status_code=403, error_code="FORBIDDEN")
