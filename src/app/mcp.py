# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Main entrypoint for FastMCP instance."""

from app.core.v1.settings import AppSettings, get_app_settings
from app.main import configure_logging

from contextlib import AsyncExitStack, asynccontextmanager
from fastapi import FastAPI
from fastmcp import FastMCP
from typing import AsyncGenerator
import httpx
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def mcp_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with AsyncExitStack() as stack:
        # Fetch OpenAPI spec
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
            resp = await client.get("/openapi.json")
            resp.raise_for_status()
            openapi_spec = resp.json()

            # Create FastMCP instance
            mcp = FastMCP.from_openapi(
                openapi_spec=openapi_spec,
                client=client,
                name="My MCP"
            )

            # Create FastMCP ASGI app and attach its lifespan
            mcp_app = mcp.http_app(path="/")
            await stack.enter_async_context(mcp_app.lifespan(app))
            logger.info("Initialized MCP lifespan")

            # Mount FastMCP app
            app.mount("/mcp", mcp_app)
            logger.info("Mounted MCP app at /mcp")

            yield

# configure logging before app creation
configure_logging(get_app_settings())

# Main FastAPI app using MCP lifespan
mcp_app = FastAPI(lifespan=mcp_lifespan)
