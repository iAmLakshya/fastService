from typing import Any

from pydantic import BaseModel
from starlette.requests import Request

from app.infrastructure.constants import HTTP_STATUS_TITLES


class ProblemDetail(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str | None = None
    errors: list[dict[str, Any]] | None = None
    extra: dict[str, Any] | None = None


class AppException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_type: str = "about:blank",
        details: dict[str, Any] | None = None,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        self.details = details or {}
        self.errors = errors
        super().__init__(message)

    def to_problem_detail(self, request: Request) -> ProblemDetail:
        return ProblemDetail(
            type=self.error_type,
            title=self._get_title(),
            status=self.status_code,
            detail=self.message,
            instance=str(request.url),
            errors=self.errors,
            extra=self.details if self.details else None,
        )

    def _get_title(self) -> str:
        return HTTP_STATUS_TITLES.get(self.status_code, "Error")
