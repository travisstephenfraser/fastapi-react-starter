"""FastAPI app factory + startup wiring."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.jwt import verify_startup
from app.core.logging import configure_logging, logger


def _client_ip(request: Request) -> str:
    """Rate-limit key. Prefer Cloudflare's connecting-IP header when behind the tunnel."""
    return request.headers.get("cf-connecting-ip") or request.client.host if request.client else "unknown"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    verify_startup()  # fetch JWKS once, assert issuer match — fail fast on misconfig
    logger.info("app.startup", env=settings.env)
    yield
    logger.info("app.shutdown")


limiter = Limiter(key_func=_client_ip, default_limits=[settings.rate_limit_default])


def create_app() -> FastAPI:
    docs_url = None if settings.env == "prod" else "/docs"
    redoc_url = None if settings.env == "prod" else "/redoc"

    app = FastAPI(
        title="fastapi-react-starter",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    origins = settings.cors_origins_list()
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,  # JWT in Authorization header, not cookies
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "env": settings.env}

    # Example slice — registered only when TEMPLATE_EXAMPLE=1. After
    # `make clean-example`, the flag flips and the import is removed.
    if settings.template_example:
        from app.features.items.router import router as items_router

        app.include_router(items_router)

    return app


app = create_app()
