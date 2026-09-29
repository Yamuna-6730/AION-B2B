from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware.logging import LoggingMiddleware
from app.api.middleware.request_timing import RequestTimingMiddleware
from app.api.routes import agents, companies, health, llm, market_discovery, missions, planner, recommendations, signals, strategy
from app.api.routes import debug_services
from app.api.routes import business_dna
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logger import configure_logging
from app.core.startup import on_shutdown, on_startup


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    await on_startup(app)
    yield
    await on_shutdown(app)


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Backend foundation for AION missions, agents, and intelligence workflows.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestTimingMiddleware)
    application.add_middleware(LoggingMiddleware)

    register_exception_handlers(application)
    application.include_router(health.router)
    application.include_router(missions.router, prefix=settings.api_v1_prefix)
    application.include_router(planner.router, prefix=settings.api_v1_prefix)
    application.include_router(companies.router, prefix=settings.api_v1_prefix)
    application.include_router(agents.router, prefix=settings.api_v1_prefix)
    application.include_router(signals.router, prefix=settings.api_v1_prefix)
    application.include_router(recommendations.router, prefix=settings.api_v1_prefix)
    application.include_router(llm.router, prefix=settings.api_v1_prefix)
    application.include_router(strategy.router, prefix=settings.api_v1_prefix)
    application.include_router(market_discovery.router, prefix=settings.api_v1_prefix)
    application.include_router(business_dna.router, prefix=settings.api_v1_prefix)
    application.include_router(debug_services.router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
