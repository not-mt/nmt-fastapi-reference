# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Repository layer for Gadget resources."""

import logging
import re
from typing import Any
from uuid import uuid4

from nmtfast.retry.v1.tenacity import tenacity_retry_log
from pymongo import ReturnDocument
from pymongo.asynchronous.collection import AsyncCollection as AsyncMongoCollection
from pymongo.asynchronous.database import AsyncDatabase as AsyncMongoDatabase
from tenacity import retry, stop_after_attempt, wait_fixed

from app.errors.v1.exceptions import ResourceNotFoundError
from app.schemas.dto.v1.gadgets import (
    GadgetCreate,
    GadgetRead,
    GadgetUpdate,
    GadgetZapTaskRecord,
)

logger = logging.getLogger(__name__)


class GadgetRepository:
    """
    Repository implementation for Gadget operations.

    Args:
        db: The asynchronous MongoDB database.
    """

    def __init__(self, db: AsyncMongoDatabase) -> None:
        self.db: AsyncMongoDatabase = db
        self.collection: AsyncMongoCollection = db["gadgets"]
        self.task_collection: AsyncMongoCollection = db["gadget_zap_tasks"]

    @staticmethod
    def _normalize_gadget(doc: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize a MongoDB gadget document for GadgetRead construction.

        Handles legacy data where:
        - The primary key may be 'gadget_id' instead of 'id'
        - The 'name' field may be missing entirely

        Args:
            doc: Raw MongoDB document dictionary.

        Returns:
            dict[str, Any]: Normalized document ready for GadgetRead.
        """
        normalized = dict(doc)
        normalized.pop("_id", None)
        if "gadget_id" in normalized and "id" not in normalized:
            normalized["id"] = normalized.pop("gadget_id")
        if "name" not in normalized:
            normalized["name"] = f"Gadget ({normalized.get('id', 'unknown')})"
        return normalized

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def gadget_create(self, gadget: GadgetCreate) -> GadgetRead:
        """
        Create a new gadget and persist it to the database.

        Args:
            gadget: The gadget data transfer object.

        Returns:
            GadgetRead: The newly created gadget instance.
        """
        new_gadget = gadget.model_dump()
        new_gadget["id"] = str(uuid4())

        await self.collection.insert_one(new_gadget)
        inserted_gadget = await self.collection.find_one({"id": new_gadget["id"]})
        logger.debug(f"Inserted gadget: {inserted_gadget}")

        return GadgetRead(**new_gadget)

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def get_by_id(self, gadget_id: str) -> GadgetRead:
        """
        Retrieve a gadget by its ID from the database.

        Args:
            gadget_id: The ID of the gadget to retrieve.

        Returns:
            GadgetRead: The retrieved gadget instance.

        Raises:
            ResourceNotFoundError: If the gadget is not found.
        """
        logger.debug(f"Fetching gadget by ID: {gadget_id}")
        db_gadget: dict[str, Any] | None = await self.collection.find_one(
            {"id": gadget_id}
        )

        if db_gadget is None:
            logger.warning(f"Gadget with ID {gadget_id} not found.")
            raise ResourceNotFoundError(gadget_id, "Gadget")

        logger.debug(f"Retrieved gadget: {db_gadget}")
        db_gadget = self._normalize_gadget(db_gadget)

        return GadgetRead(**db_gadget)

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def update_force(self, gadget_id: str, new_force: int) -> GadgetRead:
        """
        Update the force property of a gadget.

        Args:
            gadget_id: The ID of the gadget to retrieve.
            new_force: The new value for the force property.

        Returns:
            GadgetRead: The updated gadget.

        Raises:
            ResourceNotFoundError: If the gadget is not found.
        """
        logger.debug(f"Updating force for gadget ID {gadget_id} to {new_force}")
        db_gadget = await self.collection.find_one_and_update(
            {"id": gadget_id},
            {"$set": {"force": new_force}},
            return_document=ReturnDocument.AFTER,
        )

        if db_gadget is None:
            logger.warning(f"Gadget with ID {gadget_id} not found.")
            raise ResourceNotFoundError(gadget_id, "Gadget")

        logger.debug(f"Gadget ID {gadget_id} force updated to {new_force}")
        db_gadget = self._normalize_gadget(db_gadget)

        return GadgetRead(**db_gadget)

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
    ) -> tuple[list[GadgetRead], int]:
        """
        Retrieve gadgets from the database with pagination and sorting.

        Args:
            page: The page number to retrieve (1-indexed).
            page_size: The number of items per page.
            sort_by: The field name to sort by.
            sort_order: The sort direction ('asc' or 'desc').
            search: Optional search term to filter across string fields.

        Returns:
            tuple[list[GadgetRead], int]: A list of gadget instances and total count.
        """
        logger.debug("Fetching all gadgets")
        query_filter: dict = {}
        if search:
            escaped = re.escape(search)
            query_filter["$or"] = [
                {"name": {"$regex": escaped, "$options": "i"}},
                {"height": {"$regex": escaped, "$options": "i"}},
                {"mass": {"$regex": escaped, "$options": "i"}},
            ]
        total = await self.collection.count_documents(query_filter)
        direction = -1 if sort_order == "desc" else 1
        offset = (page - 1) * page_size
        cursor = (
            self.collection.find(query_filter)
            .sort(sort_by, direction)
            .skip(offset)
            .limit(page_size)
        )
        gadgets: list[GadgetRead] = []
        async for doc in cursor:
            gadgets.append(GadgetRead(**self._normalize_gadget(doc)))
        logger.debug(f"Retrieved {len(gadgets)} gadgets (total: {total})")

        return gadgets, total

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def update(self, gadget_id: str, data: GadgetUpdate) -> GadgetRead:
        """
        Update an existing gadget with partial data.

        Args:
            gadget_id: The ID of the gadget to update.
            data: The partial update data.

        Returns:
            GadgetRead: The updated gadget instance.

        Raises:
            ResourceNotFoundError: If the gadget is not found.
        """
        logger.debug(f"Updating gadget ID {gadget_id}")
        update_fields = data.model_dump(exclude_unset=True)

        db_gadget = await self.collection.find_one_and_update(
            {"id": gadget_id},
            {"$set": update_fields},
            return_document=ReturnDocument.AFTER,
        )

        if db_gadget is None:
            logger.warning(f"Gadget with ID {gadget_id} not found.")
            raise ResourceNotFoundError(gadget_id, "Gadget")

        db_gadget = self._normalize_gadget(db_gadget)
        logger.debug(f"Updated gadget ID {gadget_id}: {update_fields}")

        return GadgetRead(**db_gadget)

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def delete(self, gadget_id: str) -> None:
        """
        Delete a gadget by its ID.

        Args:
            gadget_id: The ID of the gadget to delete.

        Raises:
            ResourceNotFoundError: If the gadget is not found.
        """
        logger.debug(f"Deleting gadget ID {gadget_id}")
        result = await self.collection.delete_one({"id": gadget_id})

        if result.deleted_count == 0:
            logger.warning(f"Gadget with ID {gadget_id} not found.")
            raise ResourceNotFoundError(gadget_id, "Gadget")

        logger.debug(f"Deleted gadget ID {gadget_id}")

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def bulk_delete(self, ids: list[str]) -> int:
        """
        Delete multiple gadgets by their IDs.

        Args:
            ids: The list of gadget IDs to delete.

        Returns:
            int: The number of gadgets deleted.
        """
        logger.debug(f"Bulk deleting gadget IDs: {ids}")
        result = await self.collection.delete_many({"id": {"$in": ids}})
        logger.debug(f"Bulk deleted {result.deleted_count} gadgets")

        return result.deleted_count

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.2),
        after=tenacity_retry_log(logger),
    )
    async def bulk_update(
        self,
        ids: list[str],
        data: GadgetUpdate,
    ) -> int:
        """
        Update multiple gadgets by their IDs with the same partial data.

        Args:
            ids: The list of gadget IDs to update.
            data: The partial update data to apply to all matched gadgets.

        Returns:
            int: The number of gadgets updated.
        """
        update_fields = data.model_dump(exclude_unset=True)
        if not update_fields:
            return 0

        logger.debug(f"Bulk updating gadget IDs {ids}: {update_fields}")
        result = await self.collection.update_many(
            {"id": {"$in": ids}},
            {"$set": update_fields},
        )
        logger.debug(f"Bulk updated {result.modified_count} gadgets")

        return result.modified_count

    async def zap_task_create(
        self,
        gadget_id: str,
        task_uuid: str,
        duration: int,
    ) -> GadgetZapTaskRecord:
        """
        Create a new zap task record in MongoDB.

        Args:
            gadget_id: The ID of the gadget.
            task_uuid: The UUID of the Huey task.
            duration: The task duration in seconds.

        Returns:
            GadgetZapTaskRecord: The created task record.
        """
        from datetime import datetime

        task_record = GadgetZapTaskRecord(
            gadget_id=gadget_id,
            task_uuid=task_uuid,
            state="PENDING",
            duration=duration,
            runtime=0,
            result=None,
            created_at=datetime.now(),
            updated_at=None,
        )
        insert_doc = task_record.model_dump(by_alias=True, exclude_none=True)
        result = await self.task_collection.insert_one(insert_doc)
        task_record.id = str(result.inserted_id)
        return task_record

    async def zap_task_update(
        self,
        task_uuid: str,
        **fields: Any,
    ) -> GadgetZapTaskRecord:
        """
        Update a zap task record in MongoDB by task_uuid.

        Args:
            task_uuid: The UUID of the task to update.
            **fields: Fields to update (e.g., state, runtime, result).

        Returns:
            GadgetZapTaskRecord: The updated task record.

        Raises:
            ResourceNotFoundError: If the task record is not found.
        """
        from datetime import datetime

        update_data = {"$set": {**fields, "updated_at": datetime.now()}}
        result = await self.task_collection.find_one_and_update(
            {"task_uuid": task_uuid},
            update_data,
            return_document=ReturnDocument.AFTER,
        )
        if result is None:
            raise ResourceNotFoundError(task_uuid, "GadgetZapTaskRecord")
        result["id"] = result.pop("_id", None)

        return GadgetZapTaskRecord.model_validate(result)

    async def get_zap_task_by_uuid(
        self,
        gadget_id: str,
        task_uuid: str,
    ) -> dict[str, Any] | None:
        """
        Look up a single zap task document by task_uuid, scoped to a gadget.

        Returns None instead of raising if not found.

        Args:
            gadget_id: The ID of the gadget to scope the search.
            task_uuid: The UUID of the zap task.

        Returns:
            dict[str, Any] | None: The task document dict if found, None otherwise.
        """
        return await self.task_collection.find_one(
            {"gadget_id": gadget_id, "task_uuid": task_uuid}
        )

    async def zap_task_list(
        self,
        gadget_id: str,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        search: str | None = None,
    ) -> tuple[list[GadgetZapTaskRecord], int]:
        """
        List zap task records for a gadget with pagination.

        Args:
            gadget_id: The ID of the gadget.
            page: The page number (1-indexed).
            page_size: The number of items per page.
            sort_by: The field to sort by.
            sort_order: The sort direction ('asc' or 'desc').
            search: Optional search filter (matches on task_uuid or state).

        Returns:
            tuple[list[GadgetZapTaskRecord], int]: A list of task records and total count.
        """
        filter_query: dict[str, Any] = {"gadget_id": gadget_id}
        if search:
            filter_query["$or"] = [
                {"task_uuid": {"$regex": search, "$options": "i"}},
                {"state": {"$regex": search, "$options": "i"}},
            ]

        total = await self.task_collection.count_documents(filter_query)

        sort_spec = [(sort_by, -1 if sort_order == "desc" else 1)]
        skip = (page - 1) * page_size

        cursor = (
            self.task_collection.find(filter_query)
            .sort(sort_spec)
            .skip(skip)
            .limit(page_size)
        )
        results = await cursor.to_list(length=None)

        tasks = []
        for r in results:
            r["id"] = r.pop("_id", None)
            tasks.append(GadgetZapTaskRecord.model_validate(r))

        return tasks, total
