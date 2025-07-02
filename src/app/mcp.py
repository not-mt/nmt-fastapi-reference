# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Main entrypoint for FastMCP instance."""

import logging
from contextlib import AsyncExitStack, asynccontextmanager
from typing import AsyncGenerator

import httpx
from fastapi import FastAPI
from fastmcp import FastMCP

from app.core.v1.settings import get_app_settings
from app.main import configure_logging

logger = logging.getLogger(__name__)
settings = get_app_settings()


@asynccontextmanager
async def mcp_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Asynchronous context manager for the FastMCP application lifespan.

    This function initializes the FastMCP interface by fetching the OpenAPI spec,
    creating the FastMCP instance, attaching its ASGI app and lifespan, and mounting
    it at the configured path. Cleans up resources on shutdown.

    Args:
        app: The main FastAPI application instance.

    Yields:
        None: Used for async context management of the app's lifespan.
    """
    async with AsyncExitStack() as stack:

        # fetch OpenAPI spec
        async with httpx.AsyncClient(base_url=settings.mcp.openapi_base_url) as client:
            resp = await client.get(settings.mcp.openapi_path)
            resp.raise_for_status()
            openapi_spec = resp.json()

            # create FastMCP instance
            mcp = FastMCP.from_openapi(
                openapi_spec=openapi_spec,
                client=client,
                name=f"{settings.app_name} MCP Interface",
            )

            # create FastMCP ASGI app and attach its lifespan
            mcp_app = mcp.http_app(path="/")
            await stack.enter_async_context(mcp_app.lifespan(app))
            logger.info("Initialized MCP lifespan")

            # mount FastMCP app
            app.mount(settings.mcp.mcp_mount_path, mcp_app)
            logger.info(f"Mounted MCP app at {settings.mcp.mcp_mount_path}")

            yield


# configure logging before app creation
configure_logging(get_app_settings())

# Main FastAPI app using MCP lifespan
mcp_app = FastAPI(lifespan=mcp_lifespan)
