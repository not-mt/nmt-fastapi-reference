# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Tests for core discovery state."""

import asyncio

from app.core.v1.discovery import api_clients, api_clients_lock, required_clients


def test_api_clients_is_dict():
    """
    Test that api_clients is initialized as an empty dict.
    """
    assert isinstance(api_clients, dict)


def test_api_clients_lock_is_asyncio_lock():
    """
    Test that api_clients_lock is an asyncio.Lock.
    """
    assert isinstance(api_clients_lock, asyncio.Lock)


def test_required_clients_contains_widgets():
    """
    Test that required_clients includes the widgets service.
    """
    assert "widgets" in required_clients
