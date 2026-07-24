# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Business logic for widget resources."""

import logging
from typing import Optional

from aiokafka import AIOKafkaProducer
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
from app.layers.repository.v1.widgets import WidgetRepository
from app.schemas.dto.v1.widgets import (
    WidgetCreate,
    WidgetRead,
    WidgetUpdate,
    WidgetZap,
    WidgetZapTask,
    WidgetZapTaskRead,
)
from app.tasks.v1.widgets import WidgetZapParams, widget_zap_task

logger = logging.getLogger(__name__)


class WidgetService:
    """
    Service layer for widget business logic.

    Args:
        widget_repository: The repository for widget data operations.
        acls: List of ACLs associated with authenticated client/apikey.
        settings: The application's AppSettings object.
        cache: An implementation of AppCacheBase, for getting/setting cached data.
        kafka: Optional Kafka producer, if enabled in configuration.
    """

    def __init__(
        self,
        widget_repository: WidgetRepository,
        acls: list,
        settings: AppSettings,
        cache: AppCacheBase,
        kafka: Optional[AIOKafkaProducer],
    ) -> None:
        self.widget_repository: WidgetRepository = widget_repository
        self.acls = acls
        self.settings = settings
        self.cache = cache
        self.kafka = kafka

    async def _is_authz(self, acls: list, permission: str) -> None:
        """
        Check if the ACLs allow access to the given resource.

        Args:
            acls: List of ACLs associated with this client
            permission: Required in order to complete the requested operation.
        """
        # NOTE: by default, check_acl now raises AuthorizationError on failure
        await check_acl("widgets", acls, permission)

    async def widget_create(self, input_widget: WidgetCreate) -> WidgetRead:
        """
        Create a new widget.

        Args:
            input_widget: The widget data provided by the client.

        Returns:
            WidgetRead: The newly created widget as a Pydantic model.
        """
        await self._is_authz(self.acls, "create")
        db_widget = await self.widget_repository.widget_create(input_widget)

        # NOTE: this is a demonstration of publishing Kafka messages
        if self.settings.kafka.enabled:
            assert isinstance(self.kafka, AIOKafkaProducer)
            await self.kafka.send(
                topic="nmtfast-widgets",
                key="create-widget",
                value=WidgetRead.model_validate(db_widget),
            )

        return WidgetRead.model_validate(db_widget)

    async def widget_get_by_id(self, widget_id: int) -> WidgetRead:
        """
        Retrieve a widget by its ID.

        Args:
            widget_id: The ID of the widget to retrieve.

        Returns:
            WidgetRead: The retrieved widget.
        """
        await self._is_authz(self.acls, "read")
        db_widget = await self.widget_repository.get_by_id(widget_id)

        return WidgetRead.model_validate(db_widget)

    async def widget_list(
        self,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "id",
        sort_order: str = "asc",
        search: str | None = None,
    ) -> tuple[list[WidgetRead], int]:
        """
        Retrieve widgets with pagination and sorting.

        Args:
            page: The page number to retrieve (1-indexed).
            page_size: The number of items per page.
            sort_by: The field name to sort by.
            sort_order: The sort direction ('asc' or 'desc').
            search: Optional search term to filter results.

        Returns:
            tuple[list[WidgetRead], int]: A list of widgets and the total count.
        """
        await self._is_authz(self.acls, "read")
        db_widgets, total = await self.widget_repository.get_all(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
        )

        return [WidgetRead.model_validate(w) for w in db_widgets], total

    async def widget_update(
        self,
        widget_id: int,
        data: WidgetUpdate,
    ) -> WidgetRead:
        """
        Update an existing widget.

        Args:
            widget_id: The ID of the widget to update.
            data: The partial update data.

        Returns:
            WidgetRead: The updated widget.
        """
        await self._is_authz(self.acls, "update")
        db_widget = await self.widget_repository.update(widget_id, data)

        return WidgetRead.model_validate(db_widget)

    async def widget_delete(self, widget_id: int) -> None:
        """
        Delete a widget by its ID.

        Args:
            widget_id: The ID of the widget to delete.
        """
        await self._is_authz(self.acls, "delete")
        await self.widget_repository.delete(widget_id)

    async def widget_bulk_delete(self, ids: list[int]) -> int:
        """
        Delete multiple widgets by their IDs.

        Args:
            ids: The list of widget IDs to delete.

        Returns:
            int: The number of widgets deleted.
        """
        await self._is_authz(self.acls, "delete")

        return await self.widget_repository.bulk_delete(ids)

    async def widget_bulk_update(
        self,
        ids: list[int],
        data: WidgetUpdate,
    ) -> int:
        """
        Update multiple widgets by their IDs with the same partial data.

        Args:
            ids: The list of widget IDs to update.
            data: The partial update data to apply.

        Returns:
            int: The number of widgets updated.
        """
        await self._is_authz(self.acls, "update")

        return await self.widget_repository.bulk_update(ids, data)

    async def widget_zap(self, widget_id: int, payload: WidgetZap) -> WidgetZapTask:
        """
        Zap an existing widget by initiating an async task.

        Args:
            widget_id: The ID of the widget to zap.
            payload: The task parameters.

        Returns:
            WidgetZapTask: Status details about the new task.
        """
        await self._is_authz(self.acls, "zap")

        await self.widget_repository.get_by_id(widget_id)

        params = WidgetZapParams(
            request_id=REQUEST_ID_CONTEXTVAR.get() or "UNKNOWN",
            widget_id=widget_id,
            duration=payload.duration,
        )
        huey_task = widget_zap_task.schedule(args=[params], delay=0)

        await self.widget_repository.zap_task_create(
            widget_id=widget_id,
            task_uuid=huey_task.id,
            duration=payload.duration,
        )

        await self.widget_repository.update_last_task(
            widget_id=widget_id,
            task_uuid=huey_task.id,
            status="PENDING",
        )

        task_md = WidgetZapTask(
            uuid=huey_task.id,
            widget_id=widget_id,
            state="PENDING",
            duration=payload.duration,
            runtime=0,
            result=None,
        )
        store_task_metadata(huey_app, huey_task.id, task_md.model_dump())

        logger.info(f"Zap task {huey_task.id} scheduled for widget {widget_id}")
        return task_md

    async def widget_zap_history(
        self,
        widget_id: int,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        search: str | None = None,
    ) -> tuple[list[WidgetZapTaskRead], int]:
        """
        Retrieve zap task history for a widget with pagination.

        Args:
            widget_id: The ID of the widget.
            page: The page number (1-indexed).
            page_size: The number of items per page.
            sort_by: The field to sort by.
            sort_order: The sort direction ('asc' or 'desc').
            search: Optional search filter.

        Returns:
            tuple[list[WidgetZapTaskRead], int]: List of task history records and total count.
        """
        await self._is_authz(self.acls, "read")
        await self.widget_repository.get_by_id(widget_id)

        db_tasks, total = await self.widget_repository.zap_task_list(
            widget_id=widget_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
        )

        result_tasks = [WidgetZapTaskRead.model_validate(t) for t in db_tasks]
        return result_tasks, total

    async def widget_zap_by_uuid(
        self,
        widget_id: int,
        task_uuid: str,
    ) -> WidgetZapTask:
        """
        Retrieve a widget zap task status by UUID.

        Checks the database first. If a completed (SUCCESS or FAILED) record
        exists, returns it without querying Huey. Otherwise falls back to Huey
        task metadata/result.

        Args:
            widget_id: The ID of the widget.
            task_uuid: The UUID of the async task.

        Returns:
            WidgetZapTask: The task status and metadata.

        Raises:
            ResourceNotFoundError: Raised if the task cannot be found in DB or Huey.
            task_error: If a task error occurred during result fetch.
        """
        await self._is_authz(self.acls, "read")

        db_widget = await self.widget_repository.get_by_id(widget_id)
        logger.debug(f"Fetching zap status for widget ID {db_widget.id}")

        db_task = await self.widget_repository.get_zap_task_by_uuid(
            widget_id=widget_id,
            task_uuid=task_uuid,
        )

        if db_task is not None and db_task.state in ("SUCCESS", "FAILED"):
            logger.debug(
                f"Found completed zap task in DB for {task_uuid}: {db_task.state}"
            )
            return WidgetZapTask(
                uuid=db_task.task_uuid,
                state=db_task.state,
                widget_id=db_task.widget_id,
                duration=db_task.duration,
                runtime=db_task.runtime,
                result=db_task.result,
            )

        task_result = None
        task_error: Exception | None = None
        try:
            task_result = fetch_task_result(huey_app, task_uuid)
        except Exception as exc:
            task_error = exc

        if task_result:
            task_md = WidgetZapTask.model_validate(task_result)
            return task_md

        if task_error is not None:
            try:
                await self.widget_repository.zap_task_update(
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
        task_md = WidgetZapTask(**task_md_raw)

        return WidgetZapTask.model_validate(task_md)
