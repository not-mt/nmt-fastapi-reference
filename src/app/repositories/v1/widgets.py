# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Repository layer for Widget resources."""

import logging
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.v1.widgets import Widget
from app.schemas.v1.widgets import WidgetCreate

logger = logging.getLogger(__name__)


class WidgetRepositoryProtocol(Protocol):
    """Async Protocol defining widget repository operations."""

    async def widget_create(self, widget: WidgetCreate) -> Widget:
        """
        Create a new widget entry in the database.

        Args:
            widget: The widget schema instance.

        Returns:
            Widget: The created widget instance.
        """
        ...  # pragma: no cover

    async def get_by_id(self, widget_id: int) -> Widget | None:
        """
        Create a new widget entry in the database.

        Args:
            widget_id: The ID number of the widget.

        Returns:
            Widget | None: The created widget instance.
        """
        ...  # pragma: no cover


class WidgetRepository(WidgetRepositoryProtocol):
    """
    Repository implementation for Widget operations.

    Args:
        db: The asynchronous database session.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db: AsyncSession = db

    async def widget_create(self, widget: WidgetCreate) -> Widget:
        """
        Create a new widget and persist it to the database.

        Args:
            widget: The widget data transfer object.

        Returns:
            Widget: The newly created widget instance.
        """
        db_widget = Widget(**widget.model_dump())
        self.db.add(db_widget)
        logger.debug(f"Adding widget: {widget.model_dump()}")
        await self.db.commit()
        await self.db.refresh(db_widget)

        return db_widget

    async def get_by_id(self, widget_id: int) -> Widget | None:
        """
        Retrieve a widget by its ID from the database.

        Args:
            widget_id: The ID of the widget to retrieve.

        Returns:
            Widget | None: The retrieved widget instance, or None if not found.
        """
        logger.debug(f"Fetching widget by ID: {widget_id}")
        db_widget = await self.db.get(Widget, widget_id)

        if db_widget is None:
            logger.warning(f"Widget with ID {widget_id} not found.")
        else:
            logger.debug(f"Retrieved widget: {db_widget}")

        return db_widget
