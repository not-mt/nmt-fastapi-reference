# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Repository layer for Gadget resources."""

import logging
from typing import Any, Protocol
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from app.schemas.v1.gadgets import GadgetCreate, GadgetRead

logger = logging.getLogger(__name__)


class GadgetRepositoryProtocol(Protocol):
    """Async Protocol defining gadget repository operations."""

    async def gadget_create(self, gadget: GadgetCreate) -> GadgetRead:
        """
        Create a new gadget entry in the database.

        Args:
            gadget: The gadget schema instance.

        Returns:
            GadgetRead: The created gadget instance.
        """
        ...  # pragma: no cover

    async def get_by_id(self, gadget_id: str) -> GadgetRead | None:
        """
        Create a new gadget entry in the database.

        Args:
            gadget_id: The ID number of the gadget.

        Returns:
            GadgetRead | None: The created gadget instance.
        """
        ...  # pragma: no cover


class GadgetRepository(GadgetRepositoryProtocol):
    """
    Repository implementation for Gadget operations.

    Args:
        db: The asynchronous MongoDB database.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db: AsyncIOMotorDatabase = db
        self.collection: AsyncIOMotorCollection = db["gadgets"]

    async def gadget_create(self, gadget: GadgetCreate) -> GadgetRead:
        """
        Create a new gadget and persist it to the database.

        Args:
            gadget: The gadget data transfer object.

        Returns:
            GadgetRead: The newly created gadget instance.
        """
        new_gadget = gadget.model_dump()
        new_gadget["id"] = str(uuid4())
        await self.collection.insert_one(new_gadget)
        inserted_gadget = await self.collection.find_one({"id": new_gadget["id"]})
        logger.debug(f"Inserted gadget: {inserted_gadget}")

        return GadgetRead(**new_gadget)

    async def get_by_id(self, gadget_id: str) -> GadgetRead | None:
        """
        Retrieve a gadget by its ID from the database.

        Args:
            gadget_id: The ID of the gadget to retrieve.

        Returns:
            GadgetRead | None: The retrieved gadget instance, or None if not found.
        """
        logger.debug(f"Fetching gadget by ID: {gadget_id}")
        db_gadget: dict[str, Any] | None = await self.collection.find_one(
            {"id": gadget_id}
        )

        if db_gadget is None:
            logger.warning(f"Gadget with ID {gadget_id} not found.")
            return None
        else:
            logger.debug(f"Retrieved gadget: {db_gadget}")
            db_gadget.pop("_id", None)

        return GadgetRead(**db_gadget)
