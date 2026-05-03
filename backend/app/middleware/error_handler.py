import logging
import uuid

import sentry_sdk
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.schemas.errors import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)

_ERROR_CODE_MAP: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
}


def _status_to_code(status_code: int) -> str:
    return _ERROR_CODE_MAP.get(status_code, "UNKNOWN_ERROR")


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = str(uuid.uuid4())

        try:
            response = await call_next(request)
            return response
        except RequestValidationError as exc:
            return self._handle_validation_error(exc, request_id)
        except Exception as exc:
            return self._handle_unexpected_error(exc, request, request_id)

    def _handle_validation_error(
        self, exc: RequestValidationError, request_id: str
    ) -> JSONResponse:
        errors = exc.errors()
        if errors:
            first = errors[0]
            field_path = ".".join(
                str(loc) for loc in first.get("loc", [])
            )
            message = first.get("msg", "Validation error")
        else:
            field_path = None
            message = "Validation error"

        error_response = ErrorResponse(
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message=message,
                field=field_path or None,
            ),
            request_id=request_id,
        )

        return JSONResponse(
            status_code=422,
            content=error_response.model_dump(exclude_none=True),
        )

    def _handle_unexpected_error(
        self, exc: Exception, request: Request, request_id: str
    ) -> JSONResponse:
        logger.exception(
            "unhandled_exception",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            },
        )

        sentry_sdk.add_breadcrumb(
            category="request",
            message=f"{request.method} {request.url.path}",
            level="error",
        )
        sentry_sdk.set_context(
            "request",
            {
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
            },
        )
        sentry_sdk.capture_exception(exc)

        error_response = ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred. Please try again later.",
            ),
            request_id=request_id,
        )

        return JSONResponse(
            status_code=500,
            content=error_response.model_dump(exclude_none=True),
        )
