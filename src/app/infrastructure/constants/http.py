from enum import StrEnum


class ErrorType(StrEnum):
    NOT_FOUND = "/errors/not-found"
    VALIDATION = "/errors/validation"
    CONFLICT = "/errors/conflict"
    UNAUTHORIZED = "/errors/unauthorized"
    FORBIDDEN = "/errors/forbidden"
    RATE_LIMIT = "/errors/rate-limit"


HTTP_STATUS_TITLES: dict[int, str] = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    409: "Conflict",
    422: "Validation Error",
    429: "Too Many Requests",
    500: "Internal Server Error",
}
