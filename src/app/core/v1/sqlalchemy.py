# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""SQLAlchemy engine and session setup."""

import ssl
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

# default connection arguments; we can modify depending on config settings
connect_args = settings.sqlalchemy.connect_args

# create an engine by default, and overwrite it with SSL if necessary
async_engine = create_async_engine(
    settings.sqlalchemy.url,
    echo=settings.sqlalchemy.echo,
    connect_args=connect_args,
    echo_pool=settings.sqlalchemy.echo_pool,
    max_overflow=settings.sqlalchemy.max_overflow,
    pool_pre_ping=settings.sqlalchemy.pool_pre_ping,
    pool_size=settings.sqlalchemy.pool_size,
    pool_timeout=settings.sqlalchemy.pool_timeout,
    pool_recycle=settings.sqlalchemy.pool_recycle,
)

if settings.sqlalchemy.ssl_mode == "default":
    # NOTE: asyncpg and aiomysql require using an actual SSLContext, and
    #   not strings...
    ssl_context = ssl.create_default_context()
    connect_args["ssl"] = ssl_context

    async_engine = create_async_engine(
        url=settings.sqlalchemy.url,
        echo=settings.sqlalchemy.echo,
        connect_args=connect_args,
        echo_pool=settings.sqlalchemy.echo_pool,
        max_overflow=settings.sqlalchemy.max_overflow,
        pool_pre_ping=settings.sqlalchemy.pool_pre_ping,
        pool_size=settings.sqlalchemy.pool_size,
        pool_timeout=settings.sqlalchemy.pool_timeout,
        pool_recycle=settings.sqlalchemy.pool_recycle,
    )

async_session = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)

# Convert async URL to sync
async_url = settings.sqlalchemy.url
sync_url = (
    async_url.replace("sqlite+aiosqlite://", "sqlite://")
    .replace("mysql+aiomysql://", "mysql+pymysql://")
    .replace("postgresql+asyncpg://", "postgresql+psycopg2://")
)

# NOTE: synchronous SQLAlchemy engine and session should ONLY BE USED for
#   background tasks that are scheduled and executed by Huey
sync_engine = create_engine(
    url=sync_url,
    echo=settings.sqlalchemy.echo,
    connect_args=connect_args,
    echo_pool=settings.sqlalchemy.echo_pool,
    max_overflow=settings.sqlalchemy.max_overflow,
    pool_pre_ping=settings.sqlalchemy.pool_pre_ping,
    pool_size=settings.sqlalchemy.pool_size,
    pool_timeout=settings.sqlalchemy.pool_timeout,
    pool_recycle=settings.sqlalchemy.pool_recycle,
)
sync_session = sessionmaker(bind=sync_engine)


def with_sync_session(func):
    """
    Provide a SQLAlchemy session to a function as the 'db_session' keyword argument.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        with sync_session() as db_session:
            kwargs["db_session"] = db_session
            return func(*args, **kwargs)

    return wrapper
