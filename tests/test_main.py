# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Tests for the main FastAPI application."""

import logging
from unittest.mock import patch

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from huey import RedisExpireHuey, SqliteHuey
from nmtfast.settings.v1.schemas import Tasks

from app.core.v1.settings import AppSettings, get_app_settings
from app.core.v1.sqlalchemy import Base
from app.main import app, configure_logging, lifespan


def test_task_settings_redis_backend() -> None:
    """Test using a Huey app with Redis backend."""

    test_app_settings = AppSettings(
        tasks=Tasks(name="demo-tasks", backend="redis", url="redis://localhost:6379"),
    )

    with patch("app.core.v1.settings.get_app_settings", return_value=test_app_settings):
        # NOTE: reload the module to re-execute the module-level code
        import importlib

        from app.core.v1 import tasks

        importlib.reload(tasks)

        assert isinstance(tasks.huey_app, RedisExpireHuey)


def test_task_settings_sqlite_backend() -> None:
    """Test using a Huey app with sqlite backend."""

    test_app_settings = AppSettings(
        tasks=Tasks(name="demo-tasks", backend="sqlite"),
    )

    with patch("app.core.v1.settings.get_app_settings", return_value=test_app_settings):
        # NOTE: reload the module to re-execute the module-level code
        import importlib

        from app.core.v1 import tasks

        importlib.reload(tasks)

        assert isinstance(tasks.huey_app, SqliteHuey)


def test_logging_configuration(test_app_settings_with_loggers: AppSettings) -> None:
    """Test that the logging configuration is applied correctly."""

    # Override the get_app_settings dependency
    def override_get_app_settings() -> AppSettings:
        return test_app_settings_with_loggers

    app.dependency_overrides[get_app_settings] = override_get_app_settings

    # Reconfigure logging
    configure_logging(test_app_settings_with_loggers)

    # Assert that the log levels are set correctly
    assert logging.getLogger("test_logger_1").getEffectiveLevel() == logging.DEBUG
    assert logging.getLogger("test_logger_2").getEffectiveLevel() == logging.WARNING

    # Reset the dependency override
    app.dependency_overrides.pop(get_app_settings)


@pytest.mark.asyncio
async def test_lifespan() -> None:
    """Test the lifespan function for database schema creation."""

    test_app = FastAPI(lifespan=lifespan)
    with patch.object(Base.metadata, "create_all") as mock_create_all:
        async with LifespanManager(test_app):  # Use LifespanManager
            pass

        # Assert Base.metadata.create_all was called
        mock_create_all.assert_called_once()
