# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Business logic for gadget resources."""

import logging

from nmtfast.auth.v1.acl import check_acl
from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.middleware.v1.request_id import REQUEST_ID_CONTEXTVAR
from nmtfast.tasks.v1.huey import (
    fetch_task_metadata,
    fetch_task_result,
    store_task_metadata,
)

from app.core.v1.settings import AppSettings
from app.core.v1.tasks import huey_app
from app.errors.v1.exceptions import ResourceNotFoundError
from app.layers.repository.v1.gadgets import GadgetRepository
from app.schemas.dto.v1.gadgets import (
    GadgetCreate,
    GadgetRead,
    GadgetUpdate,
    GadgetZap,
    GadgetZapTask,
    GadgetZapTaskRead,
)
from app.tasks.v1.gadgets import GadgetZapParams, gadget_zap_task

logger = logging.getLogger(__name__)


class GadgetService:
    """
    Service layer for gadget business logic.

    Args:
        gadget_repository: The repository for gadget data operations.
        acls: List of ACLs associated with authenticated client/apikey.
        settings: The application's AppSettings object.
        cache: An implementation of AppCacheBase, for getting/setting cached data.
    """

    def __init__(
        self,
        gadget_repository: GadgetRepository,
        acls: list,
        settings: AppSettings,
        cache: AppCacheBase,
    ) -> None:
        self.gadget_repository: GadgetRepository = gadget_repository
        self.acls = acls
        self.settings = settings
        self.cache = cache

    async def _is_authz(self, acls: list, permission: str) -> None:
        """
        Check if the ACLs allow access to the given resource.

        Args:
            acls: List of ACLs associated with this client
            permission: Required in order to complete the requested operation.
        """
        # NOTE: by default, check_acl now raises AuthorizationError on failure
        await check_acl("gadgets", acls, permission)

    async def gadget_create(self, input_gadget: GadgetCreate) -> GadgetRead:
        """
        Create a new gadget.

        Args:
            input_gadget: The gadget data provided by the client.

        Returns:
            GadgetRead: The newly created gadget as a Pydantic model.
        """
        await self._is_authz(self.acls, "create")
        db_gadget = await self.gadget_repository.gadget_create(input_gadget)

        return GadgetRead.model_validate(db_gadget)

    async def gadget_get_by_id(self, gadget_id: str) -> GadgetRead:
        """
        Retrieve a gadget by its ID.

        Args:
            gadget_id: The ID of the gadget to retrieve.

        Returns:
            GadgetRead: The retrieved gadget.
        """
        await self._is_authz(self.acls, "read")
        db_gadget = await self.gadget_repository.get_by_id(gadget_id)

        return GadgetRead.model_validate(db_gadget)

    async def gadget_list(
        self,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "id",
        sort_order: str = "asc",
        search: str | None = None,
    ) -> tuple[list[GadgetRead], int]:
        """
        Retrieve gadgets with pagination and sorting.

        Args:
            page: The page number to retrieve (1-indexed).
            page_size: The number of items per page.
            sort_by: The field name to sort by.
            sort_order: The sort direction ('asc' or 'desc').
            search: Optional search term to filter results.

        Returns:
            tuple[list[GadgetRead], int]: A list of gadgets and the total count.
        """
        await self._is_authz(self.acls, "read")
        db_gadgets, total = await self.gadget_repository.get_all(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
        )

        return [GadgetRead.model_validate(g) for g in db_gadgets], total

    async def gadget_update(
        self,
        gadget_id: str,
        data: GadgetUpdate,
    ) -> GadgetRead:
        """
        Update an existing gadget.

        Args:
            gadget_id: The ID of the gadget to update.
            data: The partial update data.

        Returns:
            GadgetRead: The updated gadget.
        """
        await self._is_authz(self.acls, "update")
        db_gadget = await self.gadget_repository.update(gadget_id, data)

        return GadgetRead.model_validate(db_gadget)

    async def gadget_delete(self, gadget_id: str) -> None:
        """
        Delete a gadget by its ID.

        Args:
            gadget_id: The ID of the gadget to delete.
        """
        await self._is_authz(self.acls, "delete")
        await self.gadget_repository.delete(gadget_id)

    async def gadget_bulk_delete(self, ids: list[str]) -> int:
        """
        Delete multiple gadgets by their IDs.

        Args:
            ids: The list of gadget IDs to delete.

        Returns:
            int: The number of gadgets deleted.
        """
        await self._is_authz(self.acls, "delete")

        return await self.gadget_repository.bulk_delete(ids)

    async def gadget_bulk_update(
        self,
        ids: list[str],
        data: GadgetUpdate,
    ) -> int:
        """
        Update multiple gadgets by their IDs with the same partial data.

        Args:
            ids: The list of gadget IDs to update.
            data: The partial update data to apply.

        Returns:
            int: The number of gadgets updated.
        """
        await self._is_authz(self.acls, "update")

        return await self.gadget_repository.bulk_update(ids, data)

    async def gadget_zap(self, gadget_id: str, payload: GadgetZap) -> GadgetZapTask:
        """
        Zap a gadget by initiating an async task.

        Args:
            gadget_id: The ID of the gadget to zap.
            payload: The task parameters.

        Returns:
            GadgetZapTask: Status details about the new task.

        Raises:
            ResourceNotFoundError: If the gadget is not found.
        """
        await self._is_authz(self.acls, "zap")

        await self.gadget_repository.get_by_id(gadget_id)

        params = GadgetZapParams(
            request_id=REQUEST_ID_CONTEXTVAR.get() or "UNKNOWN",
            gadget_id=gadget_id,
            duration=payload.duration,
        )
        huey_task = gadget_zap_task.schedule(args=[params], delay=0)

        await self.gadget_repository.zap_task_create(
            gadget_id=gadget_id,
            task_uuid=huey_task.id,
            duration=payload.duration,
        )

        update_result = await self.gadget_repository.collection.update_one(
            {"id": gadget_id},
            {"$set": {"last_task_uuid": huey_task.id, "last_task_status": "PENDING"}},
        )
        if update_result.matched_count == 0:
            raise ResourceNotFoundError(gadget_id, "Gadget")

        task_md = GadgetZapTask(
            uuid=huey_task.id,
            gadget_id=gadget_id,
            state="PENDING",
            duration=payload.duration,
            runtime=0,
            result=None,
        )
        store_task_metadata(huey_app, huey_task.id, task_md.model_dump())

        logger.info(f"Zap task {huey_task.id} scheduled for gadget {gadget_id}")
        return task_md

    async def gadget_zap_history(
        self,
        gadget_id: str,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        search: str | None = None,
    ) -> tuple[list[GadgetZapTaskRead], int]:
        """
        Retrieve zap task history for a gadget with pagination.

        Args:
            gadget_id: The ID of the gadget.
            page: The page number (1-indexed).
            page_size: The number of items per page.
            sort_by: The field to sort by.
            sort_order: The sort direction ('asc' or 'desc').
            search: Optional search filter.

        Returns:
            tuple[list[GadgetZapTaskRead], int]: List of task history records and total count.
        """
        await self._is_authz(self.acls, "read")
        await self.gadget_repository.get_by_id(gadget_id)

        tasks, total = await self.gadget_repository.zap_task_list(
            gadget_id=gadget_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
        )

        result_tasks = [GadgetZapTaskRead.model_validate(t) for t in tasks]
        return result_tasks, total

    async def gadget_zap_by_uuid(
        self,
        gadget_id: str,
        task_uuid: str,
    ) -> GadgetZapTask:
        """
        Retrieve a gadget zap task status by UUID.

        Checks the database first. If a completed (SUCCESS or FAILED) record
        exists, returns it without querying Huey. Otherwise falls back to Huey
        task metadata/result.

        Args:
            gadget_id: The ID of the gadget.
            task_uuid: The UUID of the async task.

        Returns:
            GadgetZapTask: The task status and metadata.

        Raises:
            ResourceNotFoundError: If the gadget or task is not found.
            task_error: If a task error occurred during result fetch.
        """
        await self._is_authz(self.acls, "read")

        db_gadget = await self.gadget_repository.get_by_id(gadget_id)
        logger.debug(f"Fetching zap status for gadget ID {db_gadget.id}")

        db_task = await self.gadget_repository.get_zap_task_by_uuid(
            gadget_id=gadget_id,
            task_uuid=task_uuid,
        )

        if db_task is not None and db_task.get("state") in ("SUCCESS", "FAILED"):
            logger.debug(
                f"Found completed zap task in DB for {task_uuid}: {db_task['state']}"
            )
            return GadgetZapTask(
                uuid=db_task["task_uuid"],
                state=db_task["state"],
                gadget_id=db_task["gadget_id"],
                duration=db_task["duration"],
                runtime=db_task["runtime"],
                result=db_task.get("result"),
            )

        task_result = None
        task_error: Exception | None = None
        try:
            task_result = fetch_task_result(huey_app, task_uuid)
        except Exception as exc:
            task_error = exc

        if task_result:
            task_md = GadgetZapTask.model_validate(task_result)
            return task_md

        if task_error is not None:
            try:
                await self.gadget_repository.zap_task_update(
                    task_uuid=task_uuid,
                    state="FAILED",
                    result={"error": str(task_error)},
                )
            except ResourceNotFoundError:
                pass
            raise task_error

        task_md_raw = fetch_task_metadata(huey_app, task_uuid)
        if task_md_raw is None:
            logger.debug(f"Task metadata not found for {task_uuid}")
            raise ResourceNotFoundError(task_uuid, "Task")
        task_md = GadgetZapTask(**task_md_raw)

        return GadgetZapTask.model_validate(task_md)
