# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Main entrypoint for FastMCP instance; based on FastAPI app.main.app object."""

import logging
from fastapi import FastAPI
from fastmcp import FastMCP
import httpx
from contextlib import AsyncExitStack, asynccontextmanager
from typing import AsyncGenerator

# Your own app’s custom lifespan (example)
@asynccontextmanager
async def custom_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    print("App startup")
    yield
    print("App shutdown")


async def create_mcp_app():
    # Create an HTTP client for fetching OpenAPI spec and also pass to MCP
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as async_client:
        # Fetch the OpenAPI spec JSON from your FastAPI app
        response = await async_client.get("/openapi.json")
        response.raise_for_status()
        openapi_spec = response.json()

        # Create FastMCP instance from fetched spec and client
        mcp = FastMCP.from_openapi(
            openapi_spec=openapi_spec,
            client=async_client,
            name="My MCP"
        )

        # Create the FastMCP ASGI app (HTTP transport) with path prefix
        mcp_app = mcp.http_app(path="/")
        return mcp_app

@asynccontextmanager
async def composite_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with AsyncExitStack() as stack:
        print("Creating MCP app...")
        mcp_app = await create_mcp_app()

        # Enter MCP lifespan if available
        if mcp_app.lifespan is not None:
            # await stack.enter_async_context(mcp_app.lifespan)
            await stack.enter_async_context(mcp_app.lifespan(app))
            print("Executed MCP app lifespan")

        # Enter your custom lifespan
        await stack.enter_async_context(custom_lifespan(app))
        print("Executed custom lifespan")

        # Mount MCP app dynamically
        app.mount("/mcp", mcp_app)
        print("Mounted MCP app at /mcp")

        yield

# Create main FastAPI app with composite lifespan
mcp_app = FastAPI(lifespan=composite_lifespan)
