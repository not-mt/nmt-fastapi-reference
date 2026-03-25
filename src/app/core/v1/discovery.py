# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Core state for provisioned discovered services."""

import asyncio

api_clients: dict = {}
api_clients_lock: asyncio.Lock = asyncio.Lock()

# NOTE: these are names of services defined in the discovery section of the app config
required_clients: list[str] = ["widgets"]
