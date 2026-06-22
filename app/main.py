import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import init_db
from app.routes.campaigns import router as campaigns_router
from app.routes.call_logs import router as call_logs_router
from app.routes.companies import router as companies_router
from app.routes.customers import router as customers_router
from app.routes.health import router as health_router
from app.routes.webhooks import router as webhooks_router


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_prefix = settings.api_v1_prefix.rstrip("/")

    app.include_router(health_router, prefix=api_prefix)
    app.include_router(companies_router, prefix=f"{api_prefix}/companies", tags=["companies"])
    app.include_router(customers_router, prefix=f"{api_prefix}/customers", tags=["customers"])
    app.include_router(call_logs_router, prefix=f"{api_prefix}/call-logs", tags=["call-logs"])
    app.include_router(campaigns_router, prefix=f"{api_prefix}/campaigns", tags=["campaigns"])
    app.include_router(webhooks_router, prefix=f"{api_prefix}/webhooks", tags=["webhooks"])

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.on_event("startup")
    def _startup() -> None:
        # init_db()  # Commented out because the SQLite db fails to create on read-only production filesystems
        pass

    @app.exception_handler(Exception)
    async def generic_exception_handler(_: Request, exc: Exception):
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app


app = create_app()
