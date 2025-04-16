# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Database engine and session setup."""

import re
from functools import wraps

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.v1.settings import get_app_settings

settings = get_app_settings()
Base = declarative_base()  # needed for Alembic migrations

# TODO: add support in nmtfast for echo=True to see SQLAlchemy SQL statements

# NOTE: asynchronous SQLAlchemy engine and session should be used with
#   dependency injection for normal API calls
async_engine = create_async_engine(settings.database.url)
async_session = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)

# Convert async URL (e.g., "postgresql+asyncpg://") to sync (e.g., "postgresql://")
sync_url = re.sub(r"\+[^:]+", "", settings.database.url)

# NOTE: synchronous SQLAlchemy engine and session should ONLY BE USED for
#   for background tasks that are scheduled and executed by Huey
sync_engine = create_engine(sync_url)
sync_session = sessionmaker(bind=sync_engine)


def with_sync_session(func):
    """
    Provide a SQLAlchemy session to a function as the 'db' keyword argument.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        with sync_session() as db_session:
            kwargs["db_session"] = db_session
            return func(*args, **kwargs)

    return wrapper
