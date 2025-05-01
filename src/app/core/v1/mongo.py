# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""MongoDB client setup."""

from functools import wraps

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

from app.core.v1.settings import get_app_settings

settings = get_app_settings()
async_client: AsyncIOMotorClient | None = None
sync_client: MongoClient | None = None

if settings.mongo.url:
    async_client = AsyncIOMotorClient(settings.mongo.url)
    sync_client = MongoClient(settings.mongo.url)


def with_sync_mongo_db():
    """
    Provide a sync pymongo database as the 'mongo_db' keyword argument.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            kwargs["mongo_db"] = sync_client[settings.mongo.db]
            return func(*args, **kwargs)

        return wrapper

    return decorator
