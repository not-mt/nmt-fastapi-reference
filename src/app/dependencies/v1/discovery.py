# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Dependencies for upstream and service-to-service API communication."""

import logging

from fastapi import Depends
from nmtfast.discovery.v1.clients import create_api_client

from app.core.v1.cache import app_cache
from app.core.v1.discovery import api_clients, api_clients_lock, required_clients
from app.core.v1.settings import AppSettings, get_app_settings

logger = logging.getLogger(__name__)


async def get_api_clients(
    settings: AppSettings = Depends(get_app_settings),
) -> dict:
    """
    Provides a dictionary of async httpx clients, creating them lazily on first use.

    Clients are created on demand when first requested rather than at application
    startup. This prevents upstream service unavailability from blocking app startup.

    Args:
        settings: The application settings.

    Returns:
        dict: A dictionary of async httpx clients.
    """
    for client_name in required_clients:
        # NOTE: this is double-checked locking to avoid unnecessary locking after
        #   clients are initialized
        if client_name not in api_clients:
            async with api_clients_lock:
                if client_name not in api_clients:
                    logger.info(f"Lazily creating API client for '{client_name}'...")
                    api_clients[client_name] = await create_api_client(
                        settings.auth,
                        settings.discovery,
                        client_name,
                        cache=app_cache,
                    )
                    logger.info(f"API client for '{client_name}' created successfully")
    return api_clients
