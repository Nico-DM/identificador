from dotenv import load_dotenv

load_dotenv()

from env_util import env_str
from exceptions import IdentificadorError, RateLimitError
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from logging_config import configure_logging, get_logger
from middleware import RequestContextMiddleware
from routes.health import router as health_router
from routes.search import router as search_router

configure_logging()
logger = get_logger(__name__)

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    "https://identificador-web-production.vercel.app",
]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS
    if env_str("ENVIRONMENT", "development") == "development"
    else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestContextMiddleware)


@app.exception_handler(IdentificadorError)
async def identificador_error_handler(
    request: Request, exc: IdentificadorError
) -> JSONResponse:
    log_method = logger.warning if exc.http_status < 500 else logger.error
    log_method(
        exc.message,
        extra={
            "event": "domain_error",
            "code": exc.code,
            "status": exc.http_status,
            "path": request.url.path,
            "method": request.method,
        },
    )
    headers = {}
    if isinstance(exc, RateLimitError):
        headers["Retry-After"] = str(exc.retry_after)
    return JSONResponse(
        status_code=exc.http_status,
        content={"detail": exc.message, "code": exc.code},
        headers=headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning(
        "Request validation failed",
        extra={
            "event": "validation_error",
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors(),
        },
    )
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "code": "VALIDATION_ERROR"},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception(
        "Unhandled exception",
        extra={
            "event": "internal_error",
            "path": request.url.path,
            "method": request.method,
        },
    )
    is_production = env_str("ENVIRONMENT") == "production"
    detail = "Error interno del servidor" if is_production else str(exc)
    return JSONResponse(
        status_code=500,
        content={"detail": detail, "code": "INTERNAL_ERROR"},
    )


app.include_router(health_router)
app.include_router(search_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
