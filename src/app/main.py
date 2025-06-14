# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Main FastAPI application setup with routers and exception handlers."""

import logging
import logging.config
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from nmtfast.errors.v1.exceptions import UpstreamApiException
from nmtfast.logging.v1.config import create_logging_config
from nmtfast.middleware.v1.request_duration import RequestDurationMiddleware
from nmtfast.middleware.v1.request_id import RequestIDMiddleware

from app.core.v1.discovery import create_api_clients
from app.core.v1.health import set_app_not_ready, set_app_ready
from app.core.v1.kafka import create_kafka_consumers, create_kafka_producer
from app.core.v1.settings import AppSettings, get_app_settings
from app.core.v1.sqlalchemy import Base, async_engine
from app.errors.v1.exception_handlers import (
    generic_not_found_error_handler,
    index_out_of_range_error_handler,
    resource_not_found_error_handler,
    server_error_handler,
    upstream_api_exception_handler,
)
from app.errors.v1.exceptions import ResourceNotFoundError
from app.routers.v1.gadgets import gadgets_router
from app.routers.v1.health import health_router
from app.routers.v1.upstream import widgets_api_router
from app.routers.v1.widgets import widgets_router


def configure_logging(settings: AppSettings) -> None:
    """
    Configures the logging system based on the given settings.
    """
    logging_config: dict = create_logging_config(settings.logging)
    logging.config.dictConfig(logging_config)
    for logger_name, logger in settings.logging.loggers.items():
        log_level: int = getattr(logging, logger["level"].upper())
        logging.getLogger(logger_name).setLevel(log_level)


def register_routers() -> None:
    """
    Registers all API routers.
    """
    app.include_router(health_router)
    app.include_router(widgets_router)
    app.include_router(widgets_api_router)
    app.include_router(gadgets_router)


def register_exception_handlers() -> None:
    """
    Registers exception handlers for custom and built-in errors.
    """
    app.add_exception_handler(
        status.HTTP_404_NOT_FOUND,
        generic_not_found_error_handler,
    )
    app.add_exception_handler(
        ResourceNotFoundError,
        resource_not_found_error_handler,
    )
    app.add_exception_handler(
        IndexError,
        index_out_of_range_error_handler,
    )
    app.add_exception_handler(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        server_error_handler,
    )
    app.add_exception_handler(
        UpstreamApiException,
        upstream_api_exception_handler,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Handles application startup and shutdown events.

    This function is used to define actions that should be taken when the FastAPI
    application starts up and shuts down. It's especially useful for tasks like
    initializing resources (database connections) or cleaning up resources (closing
    connections).
    """
    logger: logging.Logger = logging.getLogger(__name__)
    logger.info("Lifespan started")

    logger.info("Initializing API Clients (if any)...")
    await create_api_clients()

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema created (only if necessary)")

    logger.info("Starting Kafka consumers/producer (if any)...")
    consumer_tasks = await create_kafka_consumers()
    kafka_producer = await create_kafka_producer()

    # NOTE: /health/readiness checks will pass after this
    set_app_ready()
    yield

    # NOTE: context manager handles graceful shutdown correctly--a signal
    #   handler for SIGTERM is not needed
    set_app_not_ready()

    logger.info("Shutting down Kafka consumers/producer (if any)...")
    if kafka_producer:
        await kafka_producer.stop()
    for task in consumer_tasks:
        task.cancel()

    logger.info("Lifespan ended")


# NOTE: ROOT_PATH is the equivalent of "SCRIPT_NAME" in WSGI, and specifies
#   a prefix that should be removed from  from route evaluation
root_path = os.getenv("ROOT_PATH", "")
print(f"Starting app with root_path='{root_path}'")

# Initialize FastAPI application and middleware
# NOTE: duration middleware must be first to log req IDs correctly
app: FastAPI = FastAPI(
    title="nmt-fastapi-reference",
    lifespan=lifespan,
    root_path=root_path,
)
app.add_middleware(RequestDurationMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
# Configure logging immediately after app creation
configure_logging(get_app_settings())

# Finalize application setup
register_routers()
register_exception_handlers()
