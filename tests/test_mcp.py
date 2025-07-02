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
    mock_response.json.return_value = mock_openapi_spec

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
        mock_response.raise_for_status.assert_called_once()
        mock_response.json.assert_called_once()
        mock_mcp.http_app.assert_called_once_with(path="/")
        mock_mount.assert_called_once_with("/mcp", mock_http_app)


def test_mcp_app_is_fastapi():
    """
    Test that mcp_app is a FastAPI instance.
    """
    assert isinstance(mcp_app, FastAPI)
