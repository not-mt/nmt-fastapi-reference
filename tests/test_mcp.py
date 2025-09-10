# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Tests for FastMCP application."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from app.mcp import mcp_app, mcp_lifespan


@pytest.mark.asyncio
async def test_mcp_lifespan_mounts_app():
    """
    Test that mcp_lifespan fetches OpenAPI, creates FastMCP, mounts the app, and yields.
    """
    app = FastAPI()
    mock_openapi_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0.0"},
    }

    # mock the response from httpx
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    # Implementation calls resp.json() synchronously, so set .json as a MagicMock
    mock_response.json = MagicMock(return_value=mock_openapi_spec)

    # mock AsyncClient and its context manager behavior
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    class DummyAsyncClient:
        async def __aenter__(self):
            return mock_client

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    # mock MCP http_app and its lifespan context
    mock_mcp = MagicMock()
    mock_http_app = MagicMock()

    class DummyAsyncContextManager:
        async def __aenter__(self):
            pass

        async def __aexit__(self, exc_type, exc, tb):
            pass

    mock_http_app.lifespan.return_value = DummyAsyncContextManager()
    mock_mcp.http_app.return_value = mock_http_app

    with (
        patch("app.mcp.httpx.AsyncClient", return_value=DummyAsyncClient()),
        patch("app.mcp.FastMCP.from_openapi", return_value=mock_mcp),
        patch.object(app, "mount") as mock_mount,
        patch("app.mcp.settings.mcp.openapi_base_url", "http://testserver"),
        patch("app.mcp.settings.mcp.openapi_path", "/openapi.json"),
        patch("app.mcp.settings.mcp.mcp_mount_path", "/mcp"),
    ):
        async with mcp_lifespan(app):
            pass

        mock_client.get.assert_awaited_once_with("/openapi.json")
        mock_response.json.assert_called_once()
        mock_mcp.http_app.assert_called_once()
        mock_mount.assert_called_once_with("/mcp", mock_http_app)


def test_mcp_app_is_fastapi():
    """
    Test that mcp_app is a FastAPI instance.
    """
    assert isinstance(mcp_app, FastAPI)


@pytest.mark.asyncio
async def test_mcp_lifespan_retries_and_fails():
    """
    Test that mcp_lifespan retries and raises after max_retries if OpenAPI fetch fails.
    """
    app = FastAPI()
    # Simulate failure on every get
    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = Exception("fail")
    mock_response.json = MagicMock(side_effect=Exception("fail"))
    mock_client = AsyncMock()
    mock_client.get.side_effect = Exception("fail")

    class DummyAsyncClient:
        async def __aenter__(self):
            return mock_client

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    # Patch max_retries to 2 for fast test
    with (
        patch("app.mcp.httpx.AsyncClient", return_value=DummyAsyncClient()),
        patch("app.mcp.settings.mcp.max_retries", 2),
        patch("app.mcp.settings.mcp.openapi_base_url", "http://testserver"),
        patch("app.mcp.settings.mcp.openapi_path", "/openapi.json"),
        patch("app.mcp.settings.mcp.mcp_mount_path", "/mcp"),
    ):
        with pytest.raises(Exception, match="fail"):
            async with mcp_lifespan(app):
                pass


@pytest.mark.asyncio
async def test_mcp_lifespan_openapi_not_dict():
    """
    Test that mcp_lifespan asserts if openapi_spec is not a dict.
    """
    app = FastAPI()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_response.json = MagicMock(return_value=[1, 2, 3])  # Not a dict
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    class DummyAsyncClient:
        async def __aenter__(self):
            return mock_client

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with (
        patch("app.mcp.httpx.AsyncClient", return_value=DummyAsyncClient()),
        patch("app.mcp.FastMCP.from_openapi"),
        patch("app.mcp.settings.mcp.openapi_base_url", "http://testserver"),
        patch("app.mcp.settings.mcp.openapi_path", "/openapi.json"),
        patch("app.mcp.settings.mcp.mcp_mount_path", "/mcp"),
    ):
        with pytest.raises(AssertionError):
            async with mcp_lifespan(app):
                pass
