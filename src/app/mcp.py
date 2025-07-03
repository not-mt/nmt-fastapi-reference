# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Main entrypoint for FastMCP instance."""

import asyncio
import logging
import os
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

    Raises:
        Exception: Raised if the OpenAPI spec cannot be fetched for any reason.
        AssertionError: Raised if the fetched OpenAPI spec is not a valid dictionary.
    """
    async with AsyncExitStack() as stack:

        # fetch OpenAPI spec, and retry if the API server takes a few seconds to start

        async with httpx.AsyncClient(base_url=settings.mcp.openapi_base_url) as client:
            retries = 0
            openapi_spec: dict | None = None

            while True:
                try:
                    resp = await client.get(settings.mcp.openapi_path)
                    openapi_spec = resp.json()
                    break
                except Exception as exc:
                    retries += 1
                    logger.error(
                        f"OpenAPI fetch attempt {retries} for {client.base_url}"
                        f"{settings.mcp.openapi_path} resulted in "
                        f"{exc.__class__}: {exc}"
                    )
                    await asyncio.sleep(1)
                    if retries >= settings.mcp.max_retries:
                        logger.error(
                            "Max retries reached! Failed to fetch OpenAPI spec."
                        )
                        raise

            # create FastMCP instance, but only if the spec is valid
            assert isinstance(openapi_spec, dict)
            mcp = FastMCP.from_openapi(
                openapi_spec=openapi_spec,
                client=client,
                name=f"{settings.app_name} MCP Interface",
            )

            # create FastMCP ASGI app and attach its lifespan
            mcp_inner_app = mcp.http_app(path="/")
            await stack.enter_async_context(mcp_inner_app.lifespan(app))
            logger.info("Initialized MCP lifespan")

            # mount FastMCP app
            app.mount(settings.mcp.mcp_mount_path, mcp_inner_app)
            logger.info(f"Mounted MCP app at {settings.mcp.mcp_mount_path}")

            yield


# configure logging before app creation
configure_logging(get_app_settings())

# NOTE: ROOT_PATH is the equivalent of "SCRIPT_NAME" in WSGI, and specifies
#   a prefix that should be removed from  from route evaluation
root_path = os.getenv("ROOT_PATH", "")
print(f"Starting mcp_app with root_path='{root_path}'")

# create a FastAPI app using MCP lifespan
mcp_app = FastAPI(lifespan=mcp_lifespan, root_path=root_path)
