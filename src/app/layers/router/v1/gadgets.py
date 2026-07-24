# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""This module defines API endpoints for managing gadgets."""

import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, status
from fastapi.responses import JSONResponse
from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.settings.v1.schemas import SectionACL
from pymongo.asynchronous.database import AsyncDatabase as AsyncMongoDatabase

from app.core.v1.settings import AppSettings
from app.dependencies.v1.auth import authenticate_headers, get_acls
from app.dependencies.v1.cache import get_cache
from app.dependencies.v1.mongo import get_mongo_db
from app.dependencies.v1.settings import get_settings
from app.layers.repository.v1.gadgets import GadgetRepository
from app.layers.service.v1.gadgets import GadgetService
from app.schemas.dto.v1.gadgets import (
    GadgetBulkUpdate,
    GadgetCreate,
    GadgetRead,
    GadgetUpdate,
    GadgetZap,
    GadgetZapTask,
)

logger = logging.getLogger(__name__)
gadgets_router = APIRouter(
    prefix="/v1/gadgets",
    tags=["Gadget Operations (MongoDB)"],
    dependencies=[Depends(authenticate_headers)],
)


def get_gadget_service(
    db: AsyncMongoDatabase = Depends(get_mongo_db),
    acls: list[SectionACL] = Depends(get_acls),
    settings: AppSettings = Depends(get_settings),
    cache: AppCacheBase = Depends(get_cache),
) -> GadgetService:
    """
    Dependency function to provide a GadgetService instance.

    Args:
        db: The asynchronous MongoDB database.
        acls: List of ACLs associated with authenticated client/apikey.
        settings: The application's AppSettings object.
        cache: An implementation of AppCacheBase, for getting/setting cache data.

    Returns:
        GadgetService: An instance of the gadget service.
    """
    gadget_repository = GadgetRepository(db)

    return GadgetService(gadget_repository, acls, settings, cache)


@gadgets_router.post(
    path="",
    response_model=GadgetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a gadget",
    description="Create a gadget",  # Override the docstring in Swagger UI
)
async def gadget_create(
    gadget: Annotated[
        GadgetCreate,
        Body(
            openapi_examples={
                "normal": {
                    "summary": "Create a gadget",
                    "description": (
                        "A **normal** gadget that is created successfully."
                    ),
                    "value": {
                        "name": "gadget-123",
                        "height": "15cm",
                        "mass": "0.8kg",
                        "force": 1,
                    },
                },
            },
        ),
    ],
    gadget_service: GadgetService = Depends(get_gadget_service),
) -> GadgetRead:
    """
    Create a new gadget.

    Args:
        gadget: The gadget data provided in the request.
        gadget_service: The gadget service instance.

    Returns:
        GadgetRead: The created gadget data.
    """
    logger.info(f"Attempting to create a gadget: {gadget}")
    return await gadget_service.gadget_create(gadget)


@gadgets_router.get(
    path="",
    response_model=list[GadgetRead],
    status_code=status.HTTP_200_OK,
    summary="List all gadgets",
    description="List all gadgets",
    operation_id="list_gadgets",
)
async def gadget_list(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=5000, description="Items per page")] = 10,
    sort_by: Annotated[str, Query(description="Field to sort by")] = "id",
    sort_order: Annotated[
        str, Query(pattern="^(asc|desc)$", description="Sort direction")
    ] = "asc",
    search: Annotated[str | None, Query(description="Search filter")] = None,
    gadget_service: GadgetService = Depends(get_gadget_service),
) -> JSONResponse:
    """
    List all gadgets with pagination and sorting.

    Args:
        page: The page number (1-indexed).
        page_size: The number of items per page.
        sort_by: The field to sort by.
        sort_order: The sort direction ('asc' or 'desc').
        search: Optional search filter string.
        gadget_service: The gadget service instance.

    Returns:
        JSONResponse: A JSON list of gadgets with X-Total-Count header.
    """
    logger.info("Listing all gadgets")
    gadgets, total = await gadget_service.gadget_list(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
    )
    content = [g.model_dump(mode="json") for g in gadgets]
    return JSONResponse(
        content=content,
        headers={"X-Total-Count": str(total)},
    )


@gadgets_router.get(
    "/{gadget_id}",
    response_model=GadgetRead,
    status_code=status.HTTP_200_OK,
    summary="View (read) a gadget",
    description="View (read) a gadget",  # Override the docstring in Swagger UI
)
async def gadget_get_by_id(
    gadget_id: Annotated[
        str,
        Path(description="The ID of the gadget to retrieve."),
    ],
    gadget_service: GadgetService = Depends(get_gadget_service),
) -> GadgetRead:
    """
    Retrieve a gadget by its ID.

    Args:
        gadget_id: The ID of the gadget to retrieve.
        gadget_service: The gadget service instance.

    Returns:
        GadgetRead: The retrieved gadget data.
    """
    logger.info(f"Attempting to find gadget {gadget_id}")
    return await gadget_service.gadget_get_by_id(gadget_id)


@gadgets_router.patch(
    "/{gadget_id}",
    response_model=GadgetRead,
    status_code=status.HTTP_200_OK,
    summary="Update a gadget",
    description="Update a gadget",
    operation_id="update_gadget",
)
async def gadget_update(
    gadget_id: Annotated[
        str,
        Path(description="The ID of the gadget to update."),
    ],
    gadget: Annotated[
        GadgetUpdate,
        Body(
            openapi_examples={
                "normal": {
                    "summary": "Update a gadget",
                    "description": "Update one or more fields on an existing gadget.",
                    "value": {
                        "name": "gadget-123-updated",
                        "force": 5,
                    },
                },
            },
        ),
    ],
    gadget_service: GadgetService = Depends(get_gadget_service),
) -> GadgetRead:
    """
    Update an existing gadget.

    Args:
        gadget_id: The ID of the gadget to update.
        gadget: The partial update data.
        gadget_service: The gadget service instance.

    Returns:
        GadgetRead: The updated gadget data.
    """
    logger.info(f"Attempting to update gadget {gadget_id}: {gadget}")
    return await gadget_service.gadget_update(gadget_id, gadget)


@gadgets_router.delete(
    "/{gadget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a gadget",
    description="Delete a gadget",
    operation_id="delete_gadget",
)
async def gadget_delete(
    gadget_id: Annotated[
        str,
        Path(description="The ID of the gadget to delete."),
    ],
    gadget_service: GadgetService = Depends(get_gadget_service),
) -> None:
    """
    Delete a gadget by its ID.

    Args:
        gadget_id: The ID of the gadget to delete.
        gadget_service: The gadget service instance.
    """
    logger.info(f"Attempting to delete gadget {gadget_id}")
    await gadget_service.gadget_delete(gadget_id)


@gadgets_router.post(
    "/actions/bulk/delete",
    status_code=status.HTTP_200_OK,
    summary="Bulk delete gadgets",
    description="Delete multiple gadgets by their IDs",
    operation_id="bulk_delete_gadgets",
)
async def gadget_bulk_delete(
    ids: Annotated[list[str], Body(embed=False)],
    gadget_service: GadgetService = Depends(get_gadget_service),
) -> dict[str, int]:
    """
    Delete multiple gadgets by their IDs.

    Args:
        ids: The list of gadget IDs to delete.
        gadget_service: The gadget service instance.

    Returns:
        dict[str, int]: The number of gadgets deleted.
    """
    logger.info(f"Attempting to bulk delete gadgets: {ids}")
    deleted = await gadget_service.gadget_bulk_delete(ids)

    return {"deleted": deleted}


@gadgets_router.post(
    "/actions/bulk/update",
    status_code=status.HTTP_200_OK,
    summary="Bulk update gadgets",
    description="Update multiple gadgets by their IDs with the same data",
    operation_id="bulk_update_gadgets",
)
async def gadget_bulk_update(
    payload: Annotated[GadgetBulkUpdate, Body()],
    gadget_service: GadgetService = Depends(get_gadget_service),
) -> dict[str, int]:
    """
    Update multiple gadgets by their IDs.

    Args:
        payload: The bulk update payload containing IDs and update data.
        gadget_service: The gadget service instance.

    Returns:
        dict[str, int]: The number of gadgets updated.
    """
    logger.info(f"Attempting to bulk update gadgets {payload.ids}: {payload.updates}")
    updated = await gadget_service.gadget_bulk_update(payload.ids, payload.updates)

    return {"updated": updated}


@gadgets_router.get(
    "/{gadget_id}/zap",
    status_code=status.HTTP_200_OK,
    summary="List zap task history",
    description="List zap task history for a gadget (paginated).",
    operation_id="list_gadget_zap_tasks",
)
async def gadget_zap_list(
    gadget_id: Annotated[
        str,
        Path(description="The ID of the gadget."),
    ],
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=5000, description="Items per page")] = 10,
    sort_by: Annotated[str, Query(description="Field to sort by")] = "created_at",
    sort_order: Annotated[
        str, Query(pattern="^(asc|desc)$", description="Sort direction")
    ] = "desc",
    search: Annotated[str | None, Query(description="Search filter")] = None,
    gadget_service: GadgetService = Depends(get_gadget_service),
) -> JSONResponse:
    """
    Retrieve zap task history for a gadget with pagination.

    Args:
        gadget_id: The ID of the gadget.
        page: The page number (1-indexed).
        page_size: The number of items per page.
        sort_by: The field to sort by.
        sort_order: The sort direction ('asc' or 'desc').
        search: Optional search filter.
        gadget_service: The gadget service instance.

    Returns:
        JSONResponse: A JSON list of zap task history records with X-Total-Count header.
    """
    logger.info(f"Listing zap task history for gadget {gadget_id}")
    tasks, total = await gadget_service.gadget_zap_history(
        gadget_id=gadget_id,
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


@gadgets_router.post(
    "/{gadget_id}/zap",
    response_model=GadgetZapTask,
    # TODO: add custom response which includes Location header!
    status_code=status.HTTP_202_ACCEPTED,
    summary="Zap a gadget",
    description="Zap a gadget",  # Override the docstring in Swagger UI
)
async def gadget_zap(
    gadget_id: Annotated[
        str,
        Path(description="The ID of the gadget to zap."),
    ],
    payload: Annotated[
        GadgetZap,
        Body(
            openapi_examples={
                "normal": {
                    "summary": "Zap a gadget",
                    "description": (
                        "A task is created to zap the gadget for `duration` seconds."
                    ),
                    "value": {
                        "duration": 10,
                    },
                },
            },
        ),
    ],
    gadget_service: GadgetService = Depends(get_gadget_service),
) -> GadgetZapTask:
    """
    Zaps an existing gadget.

    Args:
        gadget_id: The ID of the gadget to zap.
        payload: The gadget task parameters.
        gadget_service: The gadget service instance.

    Returns:
        GadgetZapTask: Information about the new task that was created.
    """
    logger.info(f"Attempting to zap gadget {gadget_id}: {payload}")
    return await gadget_service.gadget_zap(gadget_id, payload)


@gadgets_router.get(
    "/{gadget_id}/zap/{task_uuid}/status",
    response_model=GadgetZapTask,
    status_code=status.HTTP_200_OK,
    summary="View async task status",
    description="View async task status",  # Override the docstring in Swagger UI
)
async def gadget_zap_get_task(
    gadget_id: Annotated[
        str,
        Path(description="The ID of the gadget to retrieve."),
    ],
    task_uuid: Annotated[
        str,
        Path(description="The UUID of the async zap task."),
    ],
    gadget_service: GadgetService = Depends(get_gadget_service),
) -> GadgetZapTask:
    """
    Retrieve a zap gadget task by its UUID.

    Args:
        gadget_id: The ID of the gadget to retrieve.
        task_uuid: The UUID of the async task.
        gadget_service: The gadget service instance.

    Returns:
        GadgetZapTask: The retrieved gadget task data.
    """
    logger.info(f"Attempting to find zap status for task {task_uuid}")
    return await gadget_service.gadget_zap_by_uuid(gadget_id, task_uuid)
