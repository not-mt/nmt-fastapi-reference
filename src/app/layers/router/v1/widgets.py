# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""This module defines API endpoints for managing widgets."""

import logging
from typing import Annotated, Optional

from aiokafka import AIOKafkaProducer
from fastapi import APIRouter, Body, Depends, Path, Query, status
from fastapi.responses import JSONResponse
from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.settings.v1.schemas import SectionACL
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.v1.settings import AppSettings
from app.dependencies.v1.auth import authenticate_headers, get_acls
from app.dependencies.v1.cache import get_cache
from app.dependencies.v1.kafka import get_kafka_producer
from app.dependencies.v1.settings import get_settings
from app.dependencies.v1.sqlalchemy import get_sql_db
from app.layers.repository.v1.widgets import WidgetRepository
from app.layers.service.v1.widgets import WidgetService
from app.schemas.dto.v1.widgets import (
    WidgetBulkUpdate,
    WidgetCreate,
    WidgetRead,
    WidgetUpdate,
    WidgetZap,
    WidgetZapTask,
)

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
    cache: AppCacheBase = Depends(get_cache),
    kafka: Optional[AIOKafkaProducer] = Depends(get_kafka_producer),
) -> WidgetService:
    """
    Dependency function to provide a WidgetService instance.

    Args:
        db: The asynchronous database session.
        acls: List of ACLs associated with authenticated client/apikey.
        settings: The application's AppSettings object.
        cache: An implementation of AppCacheBase, used for getting/setting cache data.
        kafka: Optional Kafka producer, if enabled in configuration.

    Returns:
        WidgetService: An instance of the widget service.
    """
    widget_repository = WidgetRepository(db)

    return WidgetService(widget_repository, acls, settings, cache, kafka)


@widgets_router.post(
    path="",
    response_model=WidgetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a widget",
    description="Create a widget",  # Override the docstring in Swagger UI
    operation_id="create_widget",  # Custom operation ID for MCP
)
async def widget_create(
    widget: Annotated[
        WidgetCreate,
        Body(
            openapi_examples={
                "normal": {
                    "summary": "Create a widget",
                    "description": (
                        "A **normal** widget that is created successfully."
                    ),
                    "value": {
                        "name": "widget-432",
                        "height": "30cm",
                        "mass": "1.2kg",
                        "force": 1,
                    },
                },
            },
        ),
    ],
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
    path="",
    response_model=list[WidgetRead],
    status_code=status.HTTP_200_OK,
    summary="List all widgets",
    description="List all widgets",
    operation_id="list_widgets",
)
async def widget_list(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=5000, description="Items per page")] = 10,
    sort_by: Annotated[str, Query(description="Field to sort by")] = "id",
    sort_order: Annotated[
        str, Query(pattern="^(asc|desc)$", description="Sort direction")
    ] = "asc",
    search: Annotated[str | None, Query(description="Search filter")] = None,
    widget_service: WidgetService = Depends(get_widget_service),
) -> JSONResponse:
    """
    List all widgets with pagination and sorting.

    Args:
        page: The page number (1-indexed).
        page_size: The number of items per page.
        sort_by: The field to sort by.
        sort_order: The sort direction ('asc' or 'desc').
        search: Optional search filter string.
        widget_service: The widget service instance.

    Returns:
        JSONResponse: A JSON list of widgets with X-Total-Count header.
    """
    logger.info("Listing all widgets")
    widgets, total = await widget_service.widget_list(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
    )
    content = [w.model_dump(mode="json") for w in widgets]
    return JSONResponse(
        content=content,
        headers={"X-Total-Count": str(total)},
    )


@widgets_router.get(
    "/{widget_id}",
    response_model=WidgetRead,
    status_code=status.HTTP_200_OK,
    summary="View (read) a widget",
    description="View (read) a widget",  # Override the docstring in Swagger UI
    operation_id="get_widget",  # Custom operation ID for MCP
)
async def widget_get_by_id(
    widget_id: Annotated[
        int,
        Path(
            description="The ID of the widget to retrieve.",
            gt=0,
        ),
    ],
    widget_service: WidgetService = Depends(get_widget_service),
) -> WidgetRead:
    """
    Retrieve a widget by its ID.

    Args:
        widget_id: The ID of the widget to retrieve.
        widget_service: The widget service instance.

    Returns:
        WidgetRead: The retrieved widget data.
    """
    logger.info(f"Attempting to find widget {widget_id}")
    return await widget_service.widget_get_by_id(widget_id)


@widgets_router.patch(
    "/{widget_id}",
    response_model=WidgetRead,
    status_code=status.HTTP_200_OK,
    summary="Update a widget",
    description="Update a widget",
    operation_id="update_widget",
)
async def widget_update(
    widget_id: Annotated[
        int,
        Path(
            description="The ID of the widget to update.",
            gt=0,
        ),
    ],
    widget: Annotated[
        WidgetUpdate,
        Body(
            openapi_examples={
                "normal": {
                    "summary": "Update a widget",
                    "description": "Update one or more fields on an existing widget.",
                    "value": {
                        "name": "widget-432-updated",
                        "force": 5,
                    },
                },
            },
        ),
    ],
    widget_service: WidgetService = Depends(get_widget_service),
) -> WidgetRead:
    """
    Update an existing widget.

    Args:
        widget_id: The ID of the widget to update.
        widget: The partial update data.
        widget_service: The widget service instance.

    Returns:
        WidgetRead: The updated widget data.
    """
    logger.info(f"Attempting to update widget {widget_id}: {widget}")
    return await widget_service.widget_update(widget_id, widget)


@widgets_router.delete(
    "/{widget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a widget",
    description="Delete a widget",
    operation_id="delete_widget",
)
async def widget_delete(
    widget_id: Annotated[
        int,
        Path(
            description="The ID of the widget to delete.",
            gt=0,
        ),
    ],
    widget_service: WidgetService = Depends(get_widget_service),
) -> None:
    """
    Delete a widget by its ID.

    Args:
        widget_id: The ID of the widget to delete.
        widget_service: The widget service instance.
    """
    logger.info(f"Attempting to delete widget {widget_id}")
    await widget_service.widget_delete(widget_id)


@widgets_router.post(
    "/actions/bulk/delete",
    status_code=status.HTTP_200_OK,
    summary="Bulk delete widgets",
    description="Delete multiple widgets by their IDs",
    operation_id="bulk_delete_widgets",
)
async def widget_bulk_delete(
    ids: Annotated[list[int], Body(embed=False)],
    widget_service: WidgetService = Depends(get_widget_service),
) -> dict[str, int]:
    """
    Delete multiple widgets by their IDs.

    Args:
        ids: The list of widget IDs to delete.
        widget_service: The widget service instance.

    Returns:
        dict[str, int]: The number of widgets deleted.
    """
    logger.info(f"Attempting to bulk delete widgets: {ids}")
    deleted = await widget_service.widget_bulk_delete(ids)

    return {"deleted": deleted}


@widgets_router.post(
    "/actions/bulk/update",
    status_code=status.HTTP_200_OK,
    summary="Bulk update widgets",
    description="Update multiple widgets by their IDs with the same data",
    operation_id="bulk_update_widgets",
)
async def widget_bulk_update(
    payload: Annotated[WidgetBulkUpdate, Body()],
    widget_service: WidgetService = Depends(get_widget_service),
) -> dict[str, int]:
    """
    Update multiple widgets by their IDs.

    Args:
        payload: The bulk update payload containing IDs and update data.
        widget_service: The widget service instance.

    Returns:
        dict[str, int]: The number of widgets updated.
    """
    logger.info(f"Attempting to bulk update widgets {payload.ids}: {payload.updates}")
    updated = await widget_service.widget_bulk_update(payload.ids, payload.updates)

    return {"updated": updated}


@widgets_router.post(
    "/{widget_id}/zap",
    response_model=WidgetZapTask,
    # TODO: add custom response which includes Location header!
    status_code=status.HTTP_202_ACCEPTED,
    summary="Zap a widget",
    description="Zap a widget",  # Override the docstring in Swagger UI
    operation_id="zap_widget",  # Custom operation ID for MCP
)
async def widget_zap(
    widget_id: Annotated[
        int,
        Path(
            description="The ID of the widget to zap.",
            gt=0,
        ),
    ],
    payload: Annotated[
        WidgetZap,
        Body(
            openapi_examples={
                "normal": {
                    "summary": "Zap a widget",
                    "description": (
                        "A task is created to zap the widget for `duration` seconds."
                    ),
                    "value": {
                        "duration": 10,
                    },
                },
            },
        ),
    ],
    widget_service: WidgetService = Depends(get_widget_service),
) -> WidgetZapTask:
    """
    Zaps an existing widget.

    Args:
        widget_id: The ID of the widget to zap.
        payload: The widget task parameters.
        widget_service: The widget service instance.

    Returns:
        WidgetZapTask: Information about the new task that was created.
    """
    logger.info(f"Attempting to zap widget {widget_id}: {payload}")
    return await widget_service.widget_zap(widget_id, payload)


@widgets_router.get(
    "/{widget_id}/zap/{task_uuid}/status",
    response_model=WidgetZapTask,
    status_code=status.HTTP_200_OK,
    summary="View async task status",
    description="View async task status",  # Override the docstring in Swagger UI
    operation_id="get_zap_widget_status",  # Custom operation ID for MCP
)
async def widget_zap_get_task(
    widget_id: Annotated[
        int,
        Path(
            description="The ID of the widget to get zap task for.",
            gt=0,
        ),
    ],
    task_uuid: Annotated[
        str,
        Path(
            description="The UUID of the async zap task.",
        ),
    ],
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
    """
    logger.info(f"Attempting to find zap status for task {task_uuid}")
    return await widget_service.widget_zap_by_uuid(widget_id, task_uuid)
