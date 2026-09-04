# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for Kafka dependency injection functions."""

import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.v1 import kafka as kafka_module
from app.dependencies.v1.kafka import get_kafka_producer


@pytest.fixture(autouse=True)
def _reset_producer_singleton():
    """
    Reset the module-level producer singleton before and after each test.
    """
    kafka_module.kafka_producer = None
    yield
    kafka_module.kafka_producer = None


def test_get_kafka_producer_delegates_to_cached_getter():
    """
    Ensure get_kafka_producer is a plain synchronous function that delegates
    to the cached getter, reusing the already-started producer without
    starting anything.
    """
    mock_producer = MagicMock()
    mock_producer.start = AsyncMock()

    with patch.object(kafka_module, "kafka_producer", mock_producer):
        result = get_kafka_producer()

    assert result is mock_producer
    mock_producer.start.assert_not_called()


def test_get_kafka_producer_returns_none_when_disabled():
    """
    Ensure get_kafka_producer returns None when the producer was never
    initialized (Kafka disabled).
    """
    with patch.object(kafka_module, "kafka_producer", None):
        assert get_kafka_producer() is None


@pytest.mark.asyncio
async def test_dependency_seam_starts_producer_exactly_once():
    """
    Regression test for #151: after init, N dependency calls must result in
    exactly one producer start, with every call returning the same instance.
    """
    mock_producer = MagicMock()
    mock_producer.start = AsyncMock()

    mock_sk = types.SimpleNamespace(
        enabled=True,
        bootstrap_servers=["localhost:9092"],
        security_protocol="PLAINTEXT",
        sasl_mechanism="PLAIN",
        sasl_plain_username="",
        sasl_plain_password="",
    )

    with (
        patch.object(kafka_module, "_sk", mock_sk),
        patch.object(kafka_module, "_sasl_mechanism", "PLAIN"),
        patch.object(kafka_module, "_sasl_plain_username", ""),
        patch.object(kafka_module, "_sasl_plain_password", ""),
        patch.object(kafka_module, "AIOKafkaProducer", return_value=mock_producer),
    ):
        await kafka_module.init_kafka_producer()

        # NOTE: N dependency calls, as would happen across N requests
        results = [get_kafka_producer() for _ in range(10)]

    assert all(result is mock_producer for result in results)
    assert mock_producer.start.call_count == 1
