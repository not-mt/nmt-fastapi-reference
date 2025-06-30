# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Core functions for registering and enabling MCP support."""

import httpx
from fastapi import Depends, FastAPI
from fastapi_mcp import AuthConfig as FastApiMCPAuthConfig
from fastapi_mcp import FastApiMCP

from app.core.v1.settings import get_app_settings
from app.dependencies.v1.auth import authenticate_headers

settings = get_app_settings()


def register_mcp(app: FastAPI) -> FastApiMCP:
    """
    Register MCP routes on the given FastAPI app instance.

    Args:
        app: The FastAPI application instance.

    Returns:
        FastApiMCP: The configured FastApiMCP instance.
    """
    # setup MCP with selected operations and authentication
    # create a custom HTTP client that uses the FastAPI app directly

    custom_http_client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://apiserver",  # can be any dummy base URL
        timeout=10.0,
        headers=settings.mcp.headers,
    )
    mcp = FastApiMCP(
        app,
        include_operations=[
            "create_widget",
            "get_widget",
            "zap_widget",
            "get_zap_widget_status",
        ],
        auth_config=FastApiMCPAuthConfig(
            dependencies=[Depends(authenticate_headers)],
        ),
        http_client=custom_http_client,
    )
    return mcp
