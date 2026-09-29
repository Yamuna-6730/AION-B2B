from fastapi import FastAPI

from app.core.logger import app_logger


async def on_startup(app: FastAPI) -> None:
    app_logger.info("Starting AION backend", app_name=app.title)


async def on_shutdown(app: FastAPI) -> None:
    app_logger.info("Shutting down AION backend", app_name=app.title)

