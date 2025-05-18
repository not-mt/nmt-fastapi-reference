# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""MongoDB client setup."""

from functools import wraps

from pymongo import AsyncMongoClient, MongoClient

from app.core.v1.settings import get_app_settings

settings = get_app_settings()
async_client: AsyncMongoClient | None = None
sync_client: MongoClient | None = None

if settings.mongo.url:
    async_client = AsyncMongoClient(settings.mongo.url)
    sync_client = MongoClient(settings.mongo.url)


def with_sync_mongo_db():
    """
    Provide a sync pymongo database as the 'mongo_db' keyword argument.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            assert sync_client is not None, "sync_client is not initialized"
            kwargs["mongo_db"] = sync_client[settings.mongo.db]
            return func(*args, **kwargs)

        return wrapper

    return decorator
