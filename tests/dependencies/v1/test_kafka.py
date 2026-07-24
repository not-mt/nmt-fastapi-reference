# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for Kafka dependency injection functions."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.dependencies.v1.kafka import get_kafka_producer


@pytest.mark.asyncio
async def test_get_kafka_producer_calls_create_and_returns_result():
    """
    Ensure get_kafka_producer delegates to create_kafka_producer and returns
    its result (lazy-initialized singleton producer or None).
    """
    mock_producer = Mock()

    with patch(
        "app.dependencies.v1.kafka.create_kafka_producer",
        AsyncMock(return_value=mock_producer),
    ) as mock_create:
        result = await get_kafka_producer()
        assert result is mock_producer
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_get_kafka_producer_returns_none_when_disabled():
    """
    Ensure get_kafka_producer returns None when create_kafka_producer
    reports Kafka is disabled.
    """
    with patch(
        "app.dependencies.v1.kafka.create_kafka_producer",
        AsyncMock(return_value=None),
    ):
        result = await get_kafka_producer()
        assert result is None
