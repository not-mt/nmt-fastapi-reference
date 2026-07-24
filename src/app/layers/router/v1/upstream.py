# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""This module defines API endpoints for managing widgets via upsteam API."""

import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, status
from fastapi.responses import JSONResponse
from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.repositories.widgets.v1.api import WidgetApiRepository
from nmtfast.repositories.widgets.v1.schemas import (
    WidgetCreate,
    WidgetRead,
    WidgetZap,
    WidgetZapTask,
)
from nmtfast.settings.v1.schemas import SectionACL

from app.core.v1.settings import AppSettings
from app.dependencies.v1.auth import authenticate_headers, get_acls
from app.dependencies.v1.cache import get_cache
from app.dependencies.v1.discovery import get_api_clients
from app.dependencies.v1.settings import get_settings
from app.layers.service.v1.upstream import WidgetApiService

logger = logging.getLogger(__name__)
widgets_api_router = APIRouter(
    prefix="/v1/upstream",
    tags=["Widget Operations (Upstream API)"],
    dependencies=[Depends(authenticate_headers)],
)


def get_widget_service(
    api_clients: dict = Depends(get_api_clients),
    acls: list[SectionACL] = Depends(get_acls),
    settings: AppSettings = Depends(get_settings),
    cache: AppCacheBase = Depends(get_cache),
) -> WidgetApiService:
    """
    Dependency function to provide a WidgetApiService instance.

    Args:
        api_clients: Service-to-service and upstream API clients.
        acls: List of ACLs associated with authenticated client/apikey.
        settings: The application's AppSettings object.
        cache: An implementation of AppCacheBase, used for getting/setting cache data.

    Returns:
        WidgetApiService: An instance of the widget service.
    """
    widget_api_repository = WidgetApiRepository(api_clients["widgets"])

    return WidgetApiService(
        widget_api_repository,
        acls,
        settings,
        cache,
    )


@widgets_api_router.post(
    path="",
    response_model=WidgetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an API widget",
    description="Create an API widget",  # Override the docstring in Swagger UI
)
async def widget_api_create(
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
    widget_service: WidgetApiService = Depends(get_widget_service),
) -> WidgetRead:
    """
    Create a new widget.

    Upstream API exceptions (UpstreamApiException) should be caught by exception
    handlers that are registered during app startup.

    Args:
        widget: The widget data provided in the request.
        widget_service: The widget service instance.

    Returns:
        WidgetRead: The created widget data.
    """
    logger.info(f"Attempting to create a widget: {widget}")
    return await widget_service.widget_create(widget)


@widgets_api_router.get(
    "/{widget_id}",
    response_model=WidgetRead,
    status_code=status.HTTP_200_OK,
    summary="View (read) an API widget",
    description="View (read) an API widget",  # Override the docstring in Swagger UI
)
async def widget_api_get_by_id(
    widget_id: Annotated[
        int,
        Path(
            description="The ID of the widget to retrieve.",
            gt=0,
        ),
    ],
    widget_service: WidgetApiService = Depends(get_widget_service),
) -> WidgetRead:
    """
    Retrieve a widget by its ID.

    Upstream API exceptions (UpstreamApiException) should be caught by exception
    handlers that are registered during app startup.

    Args:
        widget_id: The ID of the widget to retrieve.
        widget_service: The widget service instance.

    Returns:
        WidgetRead: The retrieved widget data.
    """
    return await widget_service.widget_get_by_id(widget_id)


@widgets_api_router.get(
    "/{widget_id}/zap",
    status_code=status.HTTP_200_OK,
    summary="List API widget zap task history",
    description="List zap task history for an upstream API widget (paginated).",
    operation_id="list_api_widget_zap_tasks",
)
async def widget_api_zap_list(
    widget_id: Annotated[
        int,
        Path(description="The ID of the widget.", gt=0),
    ],
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=5000, description="Items per page")] = 10,
    sort_by: Annotated[str, Query(description="Field to sort by")] = "created_at",
    sort_order: Annotated[
        str, Query(pattern="^(asc|desc)$", description="Sort direction")
    ] = "desc",
    search: Annotated[str | None, Query(description="Search filter")] = None,
    widget_service: WidgetApiService = Depends(get_widget_service),
) -> JSONResponse:
    """
    Retrieve zap task history for an upstream API widget with pagination.

    Upstream API exceptions (UpstreamApiException) should be caught by exception
    handlers that are registered during app startup.

    Args:
        widget_id: The ID of the widget.
        page: The page number (1-indexed).
        page_size: The number of items per page.
        sort_by: The field to sort by.
        sort_order: The sort direction ('asc' or 'desc').
        search: Optional search filter.
        widget_service: The widget service instance.

    Returns:
        JSONResponse: A JSON list of zap task history records with X-Total-Count header.
    """
    logger.info(f"Listing zap task history for API widget {widget_id}")
    tasks, total = await widget_service.widget_zap_history(
        widget_id=widget_id,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
    )
    content = [t.model_dump(mode="json") for t in tasks]
    return JSONResponse(
        content=content,
        headers={"X-Total-Count": str(total)},
    )


@widgets_api_router.post(
    "/{widget_id}/zap",
    response_model=WidgetZapTask,
    # TODO: add custom response which includes Location header!
    status_code=status.HTTP_202_ACCEPTED,
    summary="Zap an API widget",
    description="Zap an API widget",  # Override the docstring in Swagger UI
)
async def widget_api_zap(
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
    widget_service: WidgetApiService = Depends(get_widget_service),
) -> WidgetZapTask:
    """
    Zaps an existing widget.

    Upstream API exceptions (UpstreamApiException) should be caught by exception
    handlers that are registered during app startup.

    Args:
        widget_id: The ID of the widget to zap.
        payload: The widget task parameters.
        widget_service: The widget service instance.

    Returns:
        WidgetZapTask: Information about the new task that was created.
    """
    logger.info(f"Attempting to zap widget {widget_id}: {payload}")

    return await widget_service.widget_zap(widget_id, payload)


@widgets_api_router.get(
    "/{widget_id}/zap/{task_uuid}/status",
    response_model=WidgetZapTask,
    status_code=status.HTTP_200_OK,
    summary="View async API task status",
    description="View async API task status",  # Override the docstring in Swagger UI
)
async def widget_api_zap_get_task(
    widget_id: Annotated[
        int,
        Path(
            description="The ID of the widget to get zap task for.",
            gt=0,
        ),
    ],
    task_uuid: Annotated[
        str,
        Path(description="The UUID of the async zap task."),
    ],
    widget_service: WidgetApiService = Depends(get_widget_service),
) -> WidgetZapTask:
    """
    Retrieve a zap widget task by its UUID.

    Upstream API exceptions (UpstreamApiException) should be caught by exception
    handlers that are registered during app startup.

    Args:
        widget_id: The ID of the widget to retrieve.
        task_uuid: The UUID of the async task.
        widget_service: The widget service instance.

    Returns:
        WidgetZapTask: The retrieved widget task data.
    """
    return await widget_service.widget_zap_by_uuid(widget_id, task_uuid)
