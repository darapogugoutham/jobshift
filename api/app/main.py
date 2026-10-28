from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import router
from app.core.config import get_settings
from app.core.errors import DomainError, domain_error_handler
from app.engines.placeholders import EngineRegistry
from app.health.routes import router as health_router

settings = get_settings()
app = FastAPI(
    title="JobShift API",
    version="1.0.0",
    description="Anonymous task inventory and import infrastructure. Analysis engines are intentionally not implemented.",
)
app.state.engine_registry = EngineRegistry()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "If-Match"],
)


@app.middleware("http")
async def security_and_request_id(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    origin = request.headers.get("origin")
    state_change = request.method in {"POST", "PUT", "PATCH", "DELETE"}
    has_session_cookie = settings.session_cookie_name in request.cookies
    if state_change and (
        (origin and origin not in settings.origins)
        or (has_session_cookie and origin not in settings.origins)
    ):
        return JSONResponse(
            status_code=403,
            content={
                "error": {
                    "code": "origin_not_allowed",
                    "message": "Request origin is not allowed.",
                    "details": None,
                    "request_id": request_id,
                }
            },
            headers={"X-Request-ID": request_id},
        )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(DomainError)
async def handle_domain(request: Request, error: DomainError):
    return await domain_error_handler(request, error)


@app.exception_handler(RequestValidationError)
async def handle_validation(request: Request, error: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Some submitted fields need attention.",
                "details": [
                    {"loc": item.get("loc"), "msg": item.get("msg"), "type": item.get("type")}
                    for item in error.errors()
                ],
                "request_id": getattr(request.state, "request_id", str(uuid4())),
            }
        },
    )


app.include_router(health_router)
app.include_router(router)
