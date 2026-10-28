from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details=None):
        self.code, self.message, self.status_code, self.details = (
            code,
            message,
            status_code,
            details,
        )


async def domain_error_handler(_request: Request, error: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details,
                "request_id": getattr(_request.state, "request_id", str(uuid4())),
            }
        },
    )
