from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.infrastructure.web.exceptions.base import AppException, ProblemDetail


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    problem = exc.to_problem_detail(request)
    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(exclude_none=True),
        media_type="application/problem+json",
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    problem = ProblemDetail(
        type="about:blank",
        title="HTTP Error",
        status=exc.status_code,
        detail=str(exc.detail),
        instance=str(request.url),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(exclude_none=True),
        media_type="application/problem+json",
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = []
    for error in exc.errors():
        loc = error.get("loc", ())
        field = str(loc[-1]) if loc else "unknown"
        errors.append(
            {
                "field": field,
                "message": error.get("msg", "Invalid value"),
                "type": error.get("type", "value_error"),
            }
        )

    problem = ProblemDetail(
        type="/errors/validation",
        title="Validation Error",
        status=422,
        detail="Request validation failed",
        instance=str(request.url),
        errors=errors,
    )
    return JSONResponse(
        status_code=422,
        content=problem.model_dump(exclude_none=True),
        media_type="application/problem+json",
    )
