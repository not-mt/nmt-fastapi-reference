# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Tests for API client dependencies with lazy initialization."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from nmtfast.discovery.v1.exceptions import ServiceConnectionError

from app.core.v1.discovery import api_clients
from app.core.v1.settings import AppSettings
from app.dependencies.v1.discovery import get_api_clients


@pytest.fixture
def mock_settings():
    """
    Fixture providing mock AppSettings.
    """
    settings = MagicMock(spec=AppSettings)
    settings.auth = "mock_auth"
    settings.discovery = "mock_discovery"
    return settings


@pytest.fixture(autouse=True)
def clear_api_clients():
    """
    Clear api_clients before and after each test.
    """
    api_clients.clear()
    yield
    api_clients.clear()


@pytest.mark.asyncio
async def test_get_api_clients_creates_client_lazily(mock_settings):
    """
    Test that get_api_clients lazily creates a client when not yet present.
    """
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    with (
        patch(
            "app.dependencies.v1.discovery.create_api_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ) as mock_create,
        patch(
            "app.dependencies.v1.discovery.app_cache",
            new_callable=AsyncMock,
        ) as mock_cache,
    ):
        result = await get_api_clients(settings=mock_settings)

        assert "widgets" in result
        assert result["widgets"] is mock_client
        mock_create.assert_awaited_once_with(
            mock_settings.auth,
            mock_settings.discovery,
            "widgets",
            cache=mock_cache,
        )


@pytest.mark.asyncio
async def test_get_api_clients_returns_existing_client(mock_settings):
    """
    Test that get_api_clients returns an existing client without recreating it.
    """
    existing_client = AsyncMock(spec=httpx.AsyncClient)
    api_clients["widgets"] = existing_client

    with patch(
        "app.dependencies.v1.discovery.create_api_client",
        new_callable=AsyncMock,
    ) as mock_create:
        result = await get_api_clients(settings=mock_settings)

        assert result["widgets"] is existing_client
        mock_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_api_clients_propagates_connection_error(mock_settings):
    """
    Test that ServiceConnectionError propagates to the caller.
    """
    with (
        patch(
            "app.dependencies.v1.discovery.create_api_client",
            new_callable=AsyncMock,
            side_effect=ServiceConnectionError("upstream down"),
        ),
        patch(
            "app.dependencies.v1.discovery.app_cache",
            new_callable=AsyncMock,
        ),
    ):
        with pytest.raises(ServiceConnectionError):
            await get_api_clients(settings=mock_settings)

    assert "widgets" not in api_clients
