# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""MongoDB client setup."""

import logging
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar

from pymongo import AsyncMongoClient, MongoClient

from app.core.v1.settings import get_app_settings

settings = get_app_settings()

# Module-level client variables accessible by tests and for backward compatibility.
# Clients are initialized lazily via get_async_client()/get_sync_client().
async_client: AsyncMongoClient | None = None
sync_client: MongoClient | None = None

T = TypeVar("T")

logger = logging.getLogger(__name__)


def get_async_client() -> AsyncMongoClient | None:
    """
    Lazily initialize and return the async MongoDB client.

    The client is created on first call if the URL setting is non-empty.

    Returns:
        AsyncMongoClient | None: The async MongoDB client, or None if not configured.
    """
    global async_client
    if async_client is None and settings.mongo.url:
        async_client = AsyncMongoClient(settings.mongo.url)
    return async_client


def get_sync_client() -> MongoClient | None:
    """
    Lazily initialize and return the synchronous MongoDB client.

    The client is created on first call if the URL setting is non-empty.

    Returns:
        MongoClient | None: The synchronous MongoDB client, or None if not configured.
    """
    global sync_client
    if sync_client is None and settings.mongo.url:
        sync_client = MongoClient(settings.mongo.url)
    return sync_client


def with_huey_mongo_session(
    func: Callable[..., Coroutine[Any, Any, T]],
) -> Callable[..., Coroutine[Any, Any, T]]:
    """
    Decorator to inject an async MongoDB database instance into Huey tasks.

    This creates a new client and database handle per task, injecting it into
    the decorated async function as 'mongo_client' and ensures proper cleanup.

    Args:
        func: The asynchronous function to be decorated. It must accept
              a `mongo_client` keyword argument.

    Returns:
        Callable[..., Coroutine[Any, Any, T]]: A new asynchronous function that
            wraps the original, managing the database connection lifecycle.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        db_name = settings.mongo.db
        huey_async_client: AsyncMongoClient = AsyncMongoClient(settings.mongo.url)
        mongo_client = huey_async_client[db_name]

        try:
            logger.debug(f"Running: {func.__qualname__} with MongoDB: {db_name}")
            kwargs["mongo_client"] = mongo_client
            result = await func(*args, **kwargs)
            return result
        except Exception as exc:
            logger.critical(
                f"Error in {func.__qualname__} using MongoDB: {exc}",
                exc_info=True,
            )
            raise
        finally:
            logger.debug(f"Cleaned up MongoDB client for: {func.__qualname__}")
            await huey_async_client.close()

    return wrapper
