from typing import Any

from app.infrastructure.constants import ErrorType
from app.infrastructure.web.exceptions.base import AppException


class NotFoundError(AppException):
    def __init__(self, resource: str, identifier: Any) -> None:
        super().__init__(
            message=f"{resource} with id '{identifier}' not found",
            status_code=404,
            error_type=ErrorType.NOT_FOUND,
            details={"resource": resource, "identifier": str(identifier)},
        )


class ValidationError(AppException):
    def __init__(
        self,
        message: str,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=422,
            error_type=ErrorType.VALIDATION,
            errors=errors,
        )


class ConflictError(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            status_code=409,
            error_type=ErrorType.CONFLICT,
            details=details,
        )


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(
            message=message,
            status_code=401,
            error_type=ErrorType.UNAUTHORIZED,
        )


class ForbiddenError(AppException):
    def __init__(self, message: str = "Access denied") -> None:
        super().__init__(
            message=message,
            status_code=403,
            error_type=ErrorType.FORBIDDEN,
        )


class RateLimitError(AppException):
    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(
            message=message,
            status_code=429,
            error_type=ErrorType.RATE_LIMIT,
        )
