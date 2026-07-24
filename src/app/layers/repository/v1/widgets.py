# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Repository layer for Widget resources."""

import logging
from typing import Any

from nmtfast.retry.v1.tenacity import tenacity_retry_log
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, or_, select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_fixed

from app.errors.v1.exceptions import ResourceNotFoundError
from app.schemas.dto.v1.widgets import WidgetCreate, WidgetUpdate
from app.schemas.orm.v1.widgets import Widget, WidgetZapTask

logger = logging.getLogger(__name__)


class WidgetRepository:
    """
    Repository implementation for Widget operations.

    Args:
        db: The asynchronous database session.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db: AsyncSession = db

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
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

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def get_by_id(self, widget_id: int) -> Widget:
        """
        Retrieve a widget by its ID from the database.

        Args:
            widget_id: The ID of the widget to retrieve.

        Returns:
            Widget: The retrieved widget instance.

        Raises:
            ResourceNotFoundError: If the widget is not found.
        """
        logger.debug(f"Fetching widget by ID: {widget_id}")
        db_widget = await self.db.get(Widget, widget_id)

        if db_widget is None:
            logger.warning(f"Widget with ID {widget_id} not found.")
            raise ResourceNotFoundError(widget_id, "Widget")
        logger.debug(f"Retrieved widget: {db_widget}")

        return db_widget

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def update_force(self, widget_id: int, new_force: int) -> Widget:
        """
        Update the force property of a widget.

        Args:
            widget_id: The ID of the widget to retrieve.
            new_force: The new value for the force property.

        Returns:
            Widget: The updated widget.

        Raises:
            ResourceNotFoundError: If the widget is not found.
        """
        logger.debug(f"Updating force for widget ID {widget_id} to {new_force}")
        db_widget = await self.db.get(Widget, widget_id)

        if db_widget is None:
            logger.warning(f"Widget with ID {widget_id} not found.")
            raise ResourceNotFoundError(widget_id, "Widget")
        logger.debug(f"Widget ID {widget_id} force updated to {new_force}")
        db_widget.force = new_force

        return db_widget

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def get_all(
        self,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "id",
        sort_order: str = "asc",
        search: str | None = None,
    ) -> tuple[list[Widget], int]:
        """
        Retrieve widgets from the database with pagination and sorting.

        Args:
            page: The page number to retrieve (1-indexed).
            page_size: The number of items per page.
            sort_by: The column name to sort by.
            sort_order: The sort direction ('asc' or 'desc').
            search: Optional search term to filter across string fields.

        Returns:
            tuple[list[Widget], int]: A list of widget instances and the total count.
        """
        logger.debug("Fetching all widgets")

        # Build optional search filter
        filters = []
        if search:
            like_term = f"%{search}%"
            filters.append(
                or_(
                    Widget.name.ilike(like_term),
                    Widget.height.ilike(like_term),
                    Widget.mass.ilike(like_term),
                )
            )

        # Total count
        count_query = select(func.count(Widget.id))
        if filters:
            count_query = count_query.where(*filters)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # Sorted + paginated query
        column = getattr(Widget, sort_by, Widget.id)
        order = column.desc() if sort_order == "desc" else column.asc()
        offset = (page - 1) * page_size
        query = select(Widget)
        if filters:
            query = query.where(*filters)
        result = await self.db.execute(
            query.order_by(order).offset(offset).limit(page_size)
        )
        widgets = list(result.scalars().all())
        logger.debug(f"Retrieved {len(widgets)} widgets (total: {total})")

        return widgets, total

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def update(self, widget_id: int, data: WidgetUpdate) -> Widget:
        """
        Update an existing widget with partial data.

        Args:
            widget_id: The ID of the widget to update.
            data: The partial update data.

        Returns:
            Widget: The updated widget instance.

        Raises:
            ResourceNotFoundError: If the widget is not found.
        """
        logger.debug(f"Updating widget ID {widget_id}")
        db_widget = await self.db.get(Widget, widget_id)

        if db_widget is None:
            logger.warning(f"Widget with ID {widget_id} not found.")
            raise ResourceNotFoundError(widget_id, "Widget")

        update_fields = data.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            setattr(db_widget, field, value)

        await self.db.commit()
        await self.db.refresh(db_widget)
        logger.debug(f"Updated widget ID {widget_id}: {update_fields}")

        return db_widget

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def delete(self, widget_id: int) -> None:
        """
        Delete a widget by its ID.

        Args:
            widget_id: The ID of the widget to delete.

        Raises:
            ResourceNotFoundError: If the widget is not found.
        """
        logger.debug(f"Deleting widget ID {widget_id}")
        db_widget = await self.db.get(Widget, widget_id)

        if db_widget is None:
            logger.warning(f"Widget with ID {widget_id} not found.")
            raise ResourceNotFoundError(widget_id, "Widget")

        await self.db.delete(db_widget)
        await self.db.commit()
        logger.debug(f"Deleted widget ID {widget_id}")

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def bulk_delete(self, ids: list[int]) -> int:
        """
        Delete multiple widgets by their IDs.

        Args:
            ids: The list of widget IDs to delete.

        Returns:
            int: The number of widgets deleted.
        """
        logger.debug(f"Bulk deleting widget IDs: {ids}")
        result = await self.db.execute(sa_delete(Widget).where(Widget.id.in_(ids)))
        await self.db.commit()
        deleted_count = result.rowcount
        logger.debug(f"Bulk deleted {deleted_count} widgets")

        return deleted_count

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def bulk_update(
        self,
        ids: list[int],
        data: "WidgetUpdate",
    ) -> int:
        """
        Update multiple widgets by their IDs with the same partial data.

        Args:
            ids: The list of widget IDs to update.
            data: The partial update data to apply to all matched widgets.

        Returns:
            int: The number of widgets updated.
        """
        update_fields = data.model_dump(exclude_unset=True)
        if not update_fields:
            return 0

        logger.debug(f"Bulk updating widget IDs {ids}: {update_fields}")
        result = await self.db.execute(
            sa_update(Widget).where(Widget.id.in_(ids)).values(**update_fields)
        )
        await self.db.commit()
        updated_count = result.rowcount
        logger.debug(f"Bulk updated {updated_count} widgets")

        return updated_count

    async def zap_task_create(
        self,
        widget_id: int,
        task_uuid: str,
        duration: int,
    ) -> WidgetZapTask:
        """
        Create a new zap task record.

        Args:
            widget_id: The ID of the widget.
            task_uuid: The UUID of the Huey task.
            duration: The task duration in seconds.

        Returns:
            WidgetZapTask: The created task record.
        """
        task_record = WidgetZapTask(
            widget_id=widget_id,
            task_uuid=task_uuid,
            state="PENDING",
            duration=duration,
        )
        self.db.add(task_record)
        await self.db.flush()
        await self.db.refresh(task_record)
        return task_record

    async def zap_task_update(
        self,
        task_uuid: str,
        **fields: Any,
    ) -> WidgetZapTask:
        """
        Update a zap task record by task_uuid.

        Args:
            task_uuid: The UUID of the task to update.
            **fields: Fields to update (e.g., state, runtime, result).

        Returns:
            WidgetZapTask: The updated task record.

        Raises:
            ResourceNotFoundError: If the task record is not found.
        """
        stmt = select(WidgetZapTask).where(WidgetZapTask.task_uuid == task_uuid)
        result = await self.db.execute(stmt)
        task_record = result.scalar_one_or_none()
        if task_record is None:
            raise ResourceNotFoundError(task_uuid, "WidgetZapTask")
        for key, value in fields.items():
            setattr(task_record, key, value)
        await self.db.flush()
        await self.db.refresh(task_record)
        return task_record

    async def zap_task_list(
        self,
        widget_id: int,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        search: str | None = None,
    ) -> tuple[list[WidgetZapTask], int]:
        """
        List zap task records for a widget with pagination.

        Args:
            widget_id: The ID of the widget.
            page: The page number (1-indexed).
            page_size: The number of items per page.
            sort_by: The field to sort by.
            sort_order: The sort direction ('asc' or 'desc').
            search: Optional search filter (matches on task_uuid or state).

        Returns:
            tuple[list[WidgetZapTask], int]: A list of task records and total count.
        """
        query = select(WidgetZapTask).where(WidgetZapTask.widget_id == widget_id)
        count_query = select(func.count()).select_from(
            select(WidgetZapTask).where(WidgetZapTask.widget_id == widget_id).subquery()
        )

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    WidgetZapTask.task_uuid.ilike(search_pattern),
                    WidgetZapTask.state.ilike(search_pattern),
                )
            )

        total = await self.db.scalar(count_query)
        if total is None:
            total = 0

        sort_column = getattr(WidgetZapTask, sort_by, WidgetZapTask.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        tasks = list(result.scalars().all())
        logger.debug(f"Retrieved {len(tasks)} tasks (total: {total})")

        return tasks, total

    async def get_zap_task_by_uuid(
        self,
        widget_id: int,
        task_uuid: str,
    ) -> WidgetZapTask | None:
        """
        Look up a single zap task record by task_uuid, scoped to a widget.

        Returns None instead of raising if not found.

        Args:
            widget_id: The ID of the widget to scope the search.
            task_uuid: The UUID of the zap task.

        Returns:
            WidgetZapTask | None: The task record if found, None otherwise.
        """
        stmt = (
            select(WidgetZapTask)
            .where(WidgetZapTask.widget_id == widget_id)
            .where(WidgetZapTask.task_uuid == task_uuid)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_last_task(
        self,
        widget_id: int,
        task_uuid: str,
        status: str,
    ) -> Widget:
        """
        Update widget with last task UUID and status.

        Args:
            widget_id: The ID of the widget.
            task_uuid: The UUID of the zap task.
            status: The task status.

        Returns:
            Widget: The updated widget.

        Raises:
            ResourceNotFoundError: If the widget is not found.
        """
        stmt = select(Widget).where(Widget.id == widget_id).with_for_update()
        result = await self.db.execute(stmt)
        widget = result.scalar_one_or_none()
        if widget is None:
            raise ResourceNotFoundError(widget_id, "Widget")
        widget.last_task_uuid = task_uuid
        widget.last_task_status = status
        await self.db.flush()
        await self.db.refresh(widget)
        return widget
