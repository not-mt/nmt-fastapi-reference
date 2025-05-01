# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""This module defines API endpoints for managing widgets."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from nmtfast.settings.v1.schemas import SectionACL
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.v1.settings import AppSettings
from app.dependencies.v1.auth import authenticate_headers, get_acls
from app.dependencies.v1.settings import get_settings
from app.dependencies.v1.sqlalchemy import get_sql_db
from app.errors.v1.exceptions import NotFoundError
from app.repositories.v1.widgets import WidgetRepository
from app.schemas.v1.widgets import (
    WidgetCreate,
    WidgetRead,
    WidgetZap,
    WidgetZapTask,
)
from app.services.v1.widgets import WidgetService

logger = logging.getLogger(__name__)
widgets_router = APIRouter(
    prefix="/v1/widgets",
    tags=["Widget Operations (SQLAlchemy)"],
    dependencies=[Depends(authenticate_headers)],
)


def get_widget_service(
    db: AsyncSession = Depends(get_sql_db),
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
async def widget_create(
    widget: WidgetCreate,
    widget_service: WidgetService = Depends(get_widget_service),
) -> WidgetRead:
    """
    Create a new widget.

    Args:
        widget: The widget data provided in the request.
        widget_service: The widget service instance.

    Returns:
        WidgetRead: The created widget data.
    """
    logger.info(f"Attempting to create a widget: {widget}")
    return await widget_service.widget_create(widget)


@widgets_router.get(
    "/{widget_id}",
    response_model=WidgetRead,
    summary="View (read) a widget",
    description="View (read) a widget",  # Override the docstring in Swagger UI
)
async def widget_get_by_id(
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
        widget = await widget_service.widget_get_by_id(widget_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"NOT FOUND: {exc}")

    return widget


@widgets_router.post(
    "/{widget_id}/zap",
    response_model=WidgetZapTask,
    # TODO: add custom response which includes Location header!
    status_code=status.HTTP_202_ACCEPTED,
    summary="Zap a widget",
    description="Zap a widget",  # Override the docstring in Swagger UI
)
async def widget_zap(
    widget_id: int,
    payload: WidgetZap,
    widget_service: WidgetService = Depends(get_widget_service),
) -> WidgetZapTask:
    """
    Zaps an existing widget.

    Args:
        widget_id: The ID of the widget to zap.
        payload: The widget task parameters.
        widget_service: The widget service instance.

    Raises:
        HTTPException: If the resource does not exist.

    Returns:
        WidgetZapTask: Information about the new task that was created.
    """
    logger.info(f"Attempting to zap widget {widget_id}: {payload}")
    try:
        return await widget_service.widget_zap(widget_id, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"NOT FOUND: {exc}")


@widgets_router.get(
    "/{widget_id}/zap/{task_uuid}/status",
    response_model=WidgetZapTask,
    summary="View async task status",
    description="View async task status",  # Override the docstring in Swagger UI
)
async def widget_zap_get_task(
    widget_id: int,
    task_uuid: str,
    widget_service: WidgetService = Depends(get_widget_service),
) -> WidgetZapTask:
    """
    Retrieve a zap widget task by its UUID.

    Args:
        widget_id: The ID of the widget to retrieve.
        task_uuid: The UUID of the async task.
        widget_service: The widget service instance.

    Returns:
        WidgetZapTask: The retrieved widget task data.

    Raises:
        HTTPException: If the resource does not exist.
    """
    try:
        task_md = await widget_service.widget_zap_by_uuid(
            widget_id,
            task_uuid,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"NOT FOUND: {exc}")

    return task_md
