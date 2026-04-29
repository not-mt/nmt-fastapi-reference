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
from app.schemas.dto.v1.gadgets import GadgetCreate, GadgetRead, GadgetUpdate

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
        db_gadget.pop("_id", None)

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
            doc.pop("_id", None)
            gadgets.append(GadgetRead(**doc))
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

        db_gadget.pop("_id", None)
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
