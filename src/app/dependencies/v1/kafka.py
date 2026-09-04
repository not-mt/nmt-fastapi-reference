# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Dependencies related to Kafka."""

from aiokafka import AIOKafkaProducer

from app.core.v1.kafka import get_cached_kafka_producer


def get_kafka_producer() -> AIOKafkaProducer | None:
    """
    Provide dependency access to the Kafka producer.

    Returns the producer started during application startup via the cached
    getter; this dependency never starts the producer itself.

    Returns:
        AIOKafkaProducer | None: An async Kafka producer, or None if Kafka support
            is not enabled.
    """
    return get_cached_kafka_producer()
