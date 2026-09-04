# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Tests for the main FastAPI application."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from huey import RedisExpireHuey, SqliteHuey
from nmtfast.settings.v1.schemas import TaskSettings, WebAuthClientSettings

from app.core.v1.settings import AppSettings, AuthSettings, get_app_settings
from app.core.v1.sqlalchemy import Base
from app.main import app, build_swagger_ui_init_oauth, configure_logging, lifespan


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


def test_custom_openapi_schema_caching() -> None:
    """
    Test that custom_openapi() generates a schema and caches it on the app.
    """

    from app.main import MD_DESCRIPTION, PROJECT_DATA, custom_openapi

    app = FastAPI()

    # Apply the custom OpenAPI generator
    app.openapi = custom_openapi(app)

    # First call: schema should be generated and cached
    schema_first = app.openapi()
    assert schema_first["info"]["title"] == "nmt-fastapi-reference"
    assert schema_first["info"]["version"] == PROJECT_DATA["project"]["version"]
    assert schema_first["info"]["summary"] == PROJECT_DATA["project"]["description"]
    assert schema_first["info"]["description"] == MD_DESCRIPTION
    assert schema_first["info"]["x-logo"]["url"].endswith("logo-teal.png")

    # Save the reference to compare later
    cached_schema = app.openapi_schema

    # Second call: should return the cached version (not regenerated)
    with patch("fastapi.openapi.utils.get_openapi") as mock_get_openapi:
        schema_second = app.openapi()
        mock_get_openapi.assert_not_called()

    assert schema_second is cached_schema


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


async def _long_running_consumer() -> None:
    """
    Coroutine that runs until cancelled, standing in for a Kafka consumer.
    """
    await asyncio.sleep(3600)


@pytest.mark.asyncio
async def test_lifespan() -> None:
    """
    Test the lifespan function with Kafka and DB schema logic: init runs
    before the readiness flag flips, one producer stop pairs with the init,
    and consumer tasks are cancelled and awaited on shutdown.
    """
    test_app = FastAPI(lifespan=lifespan)
    mock_create_all = MagicMock()  # NOTE: DO NOT AsyncMock() THIS EVER
    mock_kafka_producer = AsyncMock()
    call_order: list[str] = []

    async def _init_kafka_producer() -> AsyncMock:
        call_order.append("init_kafka_producer")
        return mock_kafka_producer

    # NOTE: use real asyncio tasks so cancel() and gather() behave for real
    consumer_task_1 = asyncio.create_task(_long_running_consumer())
    consumer_task_2 = asyncio.create_task(_long_running_consumer())

    with (
        patch.object(
            Base.metadata,
            "create_all",
            mock_create_all,
        ),
        patch(
            "app.main.create_kafka_consumers",
            new=AsyncMock(return_value=[consumer_task_1, consumer_task_2]),
        ),
        patch("app.main.init_kafka_producer", new=_init_kafka_producer),
        patch(
            "app.main.set_app_ready",
            side_effect=lambda: call_order.append("set_app_ready"),
        ),
        patch("app.main.set_app_not_ready"),
    ):
        async with LifespanManager(test_app):
            pass

        mock_create_all.assert_called_once()
        mock_kafka_producer.stop.assert_awaited_once()
        # init must run before the readiness flag flips
        assert call_order == ["init_kafka_producer", "set_app_ready"]
        # consumer tasks are cancelled AND awaited to completion
        assert consumer_task_1.done()
        assert consumer_task_1.cancelled()
        assert consumer_task_2.done()
        assert consumer_task_2.cancelled()


@pytest.mark.asyncio
async def test_lifespan_kafka_producer_none() -> None:
    """
    Test the lifespan function when no Kafka producer is initialized.
    """
    test_app = FastAPI(lifespan=lifespan)
    mock_create_all = MagicMock()  # NOTE: DO NOT AsyncMock() THIS EVER
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_context)
    mock_context.__aexit__ = AsyncMock(return_value=False)
    mock_context.run_sync = AsyncMock(side_effect=lambda f, *a, **kw: f(*a, **kw))
    mock_engine = MagicMock()
    mock_engine.begin.return_value = mock_context

    import app.main as main_module

    consumer_task = asyncio.create_task(_long_running_consumer())

    with (
        patch.object(main_module, "async_engine", mock_engine),
        patch.object(Base.metadata, "create_all", mock_create_all),
        patch(
            "app.main.create_kafka_consumers",
            new=AsyncMock(return_value=[consumer_task]),
        ),
        patch(
            "app.main.init_kafka_producer",
            new=AsyncMock(return_value=None),
        ),
        patch("app.main.set_app_ready"),
        patch("app.main.set_app_not_ready"),
    ):
        async with LifespanManager(test_app):
            pass

        mock_create_all.assert_called_once()
        # consumer task is cancelled and awaited to completion
        assert consumer_task.done()
        assert consumer_task.cancelled()


@pytest.mark.asyncio
async def test_lifespan_gathers_failed_consumer_task() -> None:
    """
    Test that lifespan shutdown completes cleanly when a consumer task has
    failed: the gather uses return_exceptions so the exception is retrieved
    rather than raised during shutdown.
    """
    test_app = FastAPI(lifespan=lifespan)
    mock_create_all = MagicMock()  # NOTE: DO NOT AsyncMock() THIS EVER

    async def _failing_consumer() -> None:
        raise RuntimeError("consumer exploded")

    consumer_task = asyncio.create_task(_failing_consumer())

    with (
        patch.object(Base.metadata, "create_all", mock_create_all),
        patch(
            "app.main.create_kafka_consumers",
            new=AsyncMock(return_value=[consumer_task]),
        ),
        patch(
            "app.main.init_kafka_producer",
            new=AsyncMock(return_value=None),
        ),
        patch("app.main.set_app_ready"),
        patch("app.main.set_app_not_ready"),
    ):
        async with LifespanManager(test_app):
            pass

    assert consumer_task.done()
    assert consumer_task.exception() is not None


def test_custom_openapi_with_swagger_authorize_url() -> None:
    """
    Test that custom_openapi() preserves OAuth2AuthorizationCode scheme
    when swagger_authorize_url is configured.
    """

    from app.main import custom_openapi

    test_settings = AppSettings(
        auth=AuthSettings(
            swagger_token_url="http://localhost/token",
            swagger_authorize_url="http://localhost/authorize",
            id_providers={},
        ),
    )

    test_app = FastAPI()
    test_app.openapi = custom_openapi(test_app)

    with patch("app.main.get_app_settings", return_value=test_settings):
        schema = test_app.openapi()

    assert schema["info"]["title"] == "nmt-fastapi-reference"
    assert test_app.openapi_schema is schema


def test_build_swagger_ui_init_oauth_with_web_auth() -> None:
    """
    Test that build_swagger_ui_init_oauth returns correct config when web_auth
    is configured.
    """
    web_auth = WebAuthClientSettings(
        provider="test-provider",
        client_id="test-client-id",
        client_secret="test-secret",
        redirect_uri="http://localhost/callback",
        scopes=["openid", "profile"],
    )
    test_settings = AppSettings(
        auth=AuthSettings(
            swagger_token_url="http://localhost/token",
            id_providers={},
            web_auth=web_auth,
        ),
    )

    result = build_swagger_ui_init_oauth(test_settings)

    assert result == {
        "clientId": "test-client-id",
        "scopes": "openid profile",
        "usePkceWithAuthorizationCodeGrant": True,
    }


def test_build_swagger_ui_init_oauth_without_web_auth() -> None:
    """
    Test that build_swagger_ui_init_oauth returns empty dict when web_auth
    is not configured.
    """
    test_settings = AppSettings()

    result = build_swagger_ui_init_oauth(test_settings)

    assert result == {}
