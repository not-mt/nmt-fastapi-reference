# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Database engine and session setup."""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.core.v1.settings import get_app_settings

settings = get_app_settings()
Base = declarative_base()  # still needed for alembic

# TODO: add support in nmtfast for echo=True to see SQLAlchemy SQL statements

async_engine = create_async_engine(settings.database.url)
async_session = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)
