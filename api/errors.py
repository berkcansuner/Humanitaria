"""Stable machine codes for API errors.

The UI maps ``code`` to a translated message; ``detail`` stays the English
string it always was (a list for 422 bodies), so existing clients keep working.
Errors without a code are shown with the generic translated message.
"""
import json
from enum import Enum

from fastapi import HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded


class ErrorCode(str, Enum):
    not_authenticated = "not_authenticated"
    forbidden = "forbidden"
    invalid_credentials = "invalid_credentials"
    email_taken = "email_taken"
    weak_password = "weak_password"
    wrong_password = "wrong_password"
    email_mismatch = "email_mismatch"
    not_found = "not_found"
    rate_limited = "rate_limited"
    message_empty = "message_empty"
    message_too_long = "message_too_long"
    conversation_limit = "conversation_limit"
    report_limit = "report_limit"
    series_mismatch = "series_mismatch"
    model_busy = "model_busy"
    quota_exhausted = "quota_exhausted"
    report_failed = "report_failed"
    chat_failed = "chat_failed"
    body_too_large = "body_too_large"
    validation_failed = "validation_failed"
    ingest_running = "ingest_running"


class ApiError(HTTPException):
    """HTTPException that also carries a machine ``code`` for the JSON body."""

    def __init__(self, status: int, code: ErrorCode, detail: str):
        super().__init__(status_code=status, detail=detail)
        self.code = code


def api_error(status: int, code: ErrorCode, detail: str) -> ApiError:
    return ApiError(status, code, detail)


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse({"detail": exc.detail, "code": exc.code.value},
                        status_code=exc.status_code, headers=exc.headers)


def _validation_code(errors: list) -> ErrorCode:
    """Most specific code for a 422: the chat message or a password field when
    that is what failed, otherwise the generic one."""
    for err in errors:
        field = (err.get("loc") or [None])[-1]
        kind = err.get("type", "")
        if field == "message" and kind != "missing":
            if kind == "string_too_long":
                return ErrorCode.message_too_long
            return ErrorCode.message_empty
        if field in ("password", "new_password") and kind == "string_too_short":
            return ErrorCode.weak_password
    return ErrorCode.validation_failed


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    resp = await request_validation_exception_handler(request, exc)
    body = json.loads(resp.body)
    body["code"] = _validation_code(exc.errors()).value
    return JSONResponse(body, status_code=resp.status_code, headers=_without_length(resp))


def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """slowapi's own response (body + Retry-After/X-RateLimit headers) plus a code."""
    resp = _rate_limit_exceeded_handler(request, exc)
    body = json.loads(resp.body)
    body["code"] = ErrorCode.rate_limited.value
    return JSONResponse(body, status_code=resp.status_code, headers=_without_length(resp))


def _without_length(resp: JSONResponse) -> dict:
    return {k: v for k, v in resp.headers.items() if k.lower() not in ("content-length", "content-type")}
