import sys

from loguru import logger

from app.core.config import settings


def configure_logging() -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.log_level,
        enqueue=True,
        backtrace=settings.environment != "production",
        diagnose=settings.environment != "production",
        serialize=settings.environment == "production",
    )


app_logger = logger.bind(component="application")
api_logger = logger.bind(component="api")
planner_logger = logger.bind(component="planner")
agent_logger = logger.bind(component="agent")
llm_logger = logger.bind(component="llm")
