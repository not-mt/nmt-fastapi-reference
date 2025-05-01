# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Repository layer for Gadget resources."""

import logging
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.v1.gadgets import Gadget
from app.schemas.v1.gadgets import GadgetCreate

logger = logging.getLogger(__name__)


class GadgetRepositoryProtocol(Protocol):
    """Async Protocol defining gadget repository operations."""

    async def gadget_create(self, gadget: GadgetCreate) -> Gadget:
        """
        Create a new gadget entry in the database.

        Args:
            gadget: The gadget schema instance.

        Returns:
            Gadget: The created gadget instance.
        """
        ...  # pragma: no cover

    async def get_by_id(self, gadget_id: int) -> Gadget | None:
        """
        Create a new gadget entry in the database.

        Args:
            gadget_id: The ID number of the gadget.

        Returns:
            Gadget | None: The created gadget instance.
        """
        ...  # pragma: no cover


class GadgetRepository(GadgetRepositoryProtocol):
    """
    Repository implementation for Gadget operations.

    Args:
        db: The asynchronous database session.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db: AsyncSession = db

    async def gadget_create(self, gadget: GadgetCreate) -> Gadget:
        """
        Create a new gadget and persist it to the database.

        Args:
            gadget: The gadget data transfer object.

        Returns:
            Gadget: The newly created gadget instance.
        """
        db_gadget = Gadget(**gadget.model_dump())
        self.db.add(db_gadget)
        logger.debug(f"Adding gadget: {gadget.model_dump()}")
        await self.db.commit()
        await self.db.refresh(db_gadget)

        return db_gadget

    async def get_by_id(self, gadget_id: int) -> Gadget | None:
        """
        Retrieve a gadget by its ID from the database.

        Args:
            gadget_id: The ID of the gadget to retrieve.

        Returns:
            Gadget | None: The retrieved gadget instance, or None if not found.
        """
        logger.debug(f"Fetching gadget by ID: {gadget_id}")
        db_gadget = await self.db.get(Gadget, gadget_id)

        if db_gadget is None:
            logger.warning(f"Gadget with ID {gadget_id} not found.")
        else:
            logger.debug(f"Retrieved gadget: {db_gadget}")

        return db_gadget
