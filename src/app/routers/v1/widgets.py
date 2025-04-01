# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""
Widget API endpoints.

This module defines API endpoints for managing widgets, including creating widgets.
It utilizes FastAPI's dependency injection to handle database sessions.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from nmtfast.settings.v1.schemas import SectionACL
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.v1.settings import AppSettings
from app.dependencies.v1.auth import authenticate_headers, get_acls
from app.dependencies.v1.database import get_db
from app.dependencies.v1.settings import get_settings
from app.errors.v1.exceptions import NotFoundError
from app.repositories.v1.widgets import WidgetRepository
from app.schemas.v1.widgets import WidgetCreate, WidgetRead
from app.services.v1.widgets import WidgetService

logger = logging.getLogger(__name__)
widgets_router = APIRouter(
    prefix="/v1/widgets",
    tags=["Widget Operations"],
    dependencies=[Depends(authenticate_headers)],
)


def get_widget_service(
    db: AsyncSession = Depends(get_db),
    acls: list[SectionACL] = Depends(get_acls),
    settings: AppSettings = Depends(get_settings),
) -> WidgetService:
    """
    Dependency function to provide a WidgetService instance.

    Args:
        db: The asynchronous database session.
        acls: List of ACLs associated with authenticated client/apikey.
        settings: The application's AppSettings object.

    Returns:
        WidgetService: An instance of the widget service.
    """
    widget_repository = WidgetRepository(db)

    return WidgetService(widget_repository, acls, settings)


@widgets_router.post(
    "/",
    response_model=WidgetRead,
    summary="Create a widget",
    description="Create a widget",  # Override the docstring in Swagger UI
)
async def create_widget(
    widget: WidgetCreate,
    widget_service: WidgetService = Depends(get_widget_service),
) -> WidgetRead:
    """
    Create a new widget via the API.

    Args:
        widget: The widget data provided in the request.
        widget_service: The widget service instance.

    Returns:
        WidgetRead: The created widget data.
    """
    logger.info(f"Attempting to create a widget: {widget}")
    return await widget_service.create_widget(widget)


@widgets_router.get(
    "/{widget_id}",
    response_model=WidgetRead,
    summary="View (read) a widget",
    description="View (read) a widget",  # Override the docstring in Swagger UI
)
async def get_widget_by_id(
    widget_id: int,
    widget_service: WidgetService = Depends(get_widget_service),
) -> WidgetRead:
    """
    Retrieve a widget by its ID.

    Args:
        widget_id: The ID of the widget to retrieve.
        widget_service: The widget service instance.

    Returns:
        WidgetRead: The retrieved widget data.

    Raises:
        HTTPException: If the resource does not exist.
    """
    try:
        widget = await widget_service.get_widget_by_id(widget_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"NOT FOUND: {exc}")

    return widget
