# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Tests for the main FastAPI application."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from huey import RedisExpireHuey, SqliteHuey
from nmtfast.settings.v1.schemas import TaskSettings

from app.core.v1.settings import AppSettings, get_app_settings
from app.core.v1.sqlalchemy import Base
from app.main import app, configure_logging, lifespan


def test_task_settings_redis_backend() -> None:
    """
    Test using a Huey app with Redis backend.
    """

    test_app_settings = AppSettings(
        tasks=TaskSettings(
            name="demo-tasks", backend="redis", url="redis://localhost:6379"
        ),
    )

    with patch("app.core.v1.settings.get_app_settings", return_value=test_app_settings):

        # NOTE: reload the module to re-execute the module-level code
        import importlib

        from app.core.v1 import tasks

        importlib.reload(tasks)

        assert isinstance(tasks.huey_app, RedisExpireHuey)


def test_task_settings_sqlite_backend() -> None:
    """
    Test using a Huey app with sqlite backend.
    """

    test_app_settings = AppSettings(
        tasks=TaskSettings(name="demo-tasks", backend="sqlite"),
    )

    with patch("app.core.v1.settings.get_app_settings", return_value=test_app_settings):

        # NOTE: reload the module to re-execute the module-level code
        import importlib

        from app.core.v1 import tasks

        importlib.reload(tasks)

        assert isinstance(tasks.huey_app, SqliteHuey)


def test_logging_configuration(test_app_settings_with_loggers: AppSettings) -> None:
    """
    Test that the logging configuration is applied correctly.
    """

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
    """
    Test the lifespan function with Kafka and DB schema logic.
    """
    test_app = FastAPI(lifespan=lifespan)
    mock_create_all = MagicMock()  # NOTE: DO NOT AsyncMock() THIS EVER
    mock_consumer_task_1 = MagicMock()
    mock_consumer_task_2 = MagicMock()
    mock_kafka_producer = AsyncMock()

    with (
        patch.object(
            Base.metadata,
            "create_all",
            mock_create_all,
        ),
        patch(
            "app.core.v1.discovery.required_clients",
            new=[],
        ),
        patch(
            "app.main.create_kafka_consumers",
            return_value=[mock_consumer_task_1, mock_consumer_task_2],
        ),
        patch(
            "app.main.create_kafka_producer",
            return_value=mock_kafka_producer,
        ),
    ):
        async with LifespanManager(test_app):
            pass

        mock_create_all.assert_called_once()
        mock_kafka_producer.stop.assert_awaited_once()
        mock_consumer_task_1.cancel.assert_called_once()
        mock_consumer_task_2.cancel.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_kafka_producer_none() -> None:
    """
    Test the lifespan function when no Kafka producer is returned.
    """
    test_app = FastAPI(lifespan=lifespan)
    mock_create_all = MagicMock()  # NOTE: DO NOT AsyncMock() THIS EVER
    mock_consumer_task = MagicMock()

    with (
        patch.object(Base.metadata, "create_all", mock_create_all),
        patch("app.core.v1.discovery.required_clients", new=[]),
        patch("app.main.create_kafka_consumers", return_value=[mock_consumer_task]),
        patch("app.main.create_kafka_producer", return_value=None),
    ):
        async with LifespanManager(test_app):
            pass

        mock_create_all.assert_called_once()
        # kafka_producer is None, so nothing to await
        mock_consumer_task.cancel.assert_called_once()
