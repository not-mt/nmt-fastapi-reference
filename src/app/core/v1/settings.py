# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Application settings and defaults, defined with pydantic-settings."""

import logging
from typing import Literal

from nmtfast.settings.v1.config_files import get_config_files, load_config
from nmtfast.settings.v1.schemas import (
    AuthSettings,
    CacheSettings,
    LoggingSettings,
    Tasks,
)
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class SqlAlchemySettings(BaseModel):
    """SQLAlchemy database settings model."""

    url: str = "sqlite+aiosqlite:///./development.sqlite"
    ssl_mode: Literal["none", "default"] = "none"
    echo: bool = False
    connect_args: dict = {}
    echo_pool: bool = False
    max_overflow: int = 10
    pool_pre_ping: bool = True
    pool_size: int = 4
    pool_timeout: int = 30
    pool_recycle: int = 300


class MongoSettings(BaseModel):
    """MongoDB database settings model."""

    url: str = (
        "mongodb+srv://FIXME_username:FIXME_PASSWORD"
        "@cluster0.FIXME.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    )
    db: str = "nmt-fastapi-reference"


class AppSettings(BaseSettings):
    """Application settings model."""

    version: int = 1
    app_name: str = "My FastAPI App"
    sqlalchemy: SqlAlchemySettings = SqlAlchemySettings()
    mongo: MongoSettings = MongoSettings()
    auth: AuthSettings = AuthSettings(
        swagger_token_url="https://some.domain.tld/token",
        id_providers={},
        clients={},
        api_keys={},
    )
    logging: LoggingSettings = LoggingSettings()
    tasks: Tasks = Tasks(
        name="FIXME",
        backend="sqlite",
        url="redis://:FIXME_password@FIXME_host:6379/FIXME_db_number",
        sqlite_filename="./huey.sqlite",
    )
    cache: CacheSettings = CacheSettings(
        name="nmt-fastapi-reference",
        backend="huey",
        ttl=3600 * 4,
    )

    model_config = SettingsConfigDict(extra="ignore")


def get_app_settings() -> AppSettings:
    """
    Dependency function to provide settings.

    Returns:
        AppSettings: The application settings.
    """
    return _settings


_config_data: dict = load_config(get_config_files())
_settings: AppSettings = AppSettings(**_config_data)
