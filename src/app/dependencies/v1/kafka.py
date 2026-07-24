# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Dependencies related to Kafka."""

from aiokafka import AIOKafkaProducer
from fastapi import Depends

from app.core.v1.kafka import create_kafka_producer
from app.core.v1.settings import AppSettings, get_app_settings


async def get_kafka_producer(
    settings: AppSettings = Depends(get_app_settings),
) -> AIOKafkaProducer | None:
    """
    Provide dependency access to the Kafka producer.

    Lazily initializes the producer on first use by delegating to
    create_kafka_producer(), which caches the instance as a module-level
    singleton. Subsequent calls reuse the already-started producer.

    Args:
        settings: The application settings.

    Returns:
        AIOKafkaProducer | None: An async Kafka producer, or None if Kafka support
            is not enabled.
    """
    return await create_kafka_producer()
