# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for repository layer using MongoDB."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.errors.v1.exceptions import ResourceNotFoundError
from app.layers.repository.v1.gadgets import GadgetRepository
from app.schemas.dto.v1.gadgets import (
    GadgetCreate,
    GadgetRead,
    GadgetUpdate,
    GadgetZapTaskRecord,
)


class _MockAsyncCursor:
    """
    Helper to mock MongoDB async cursor with sync chaining.
    """

    def __init__(self, results):
        self._results = list(results)
        self.sort = MagicMock(return_value=self)
        self.skip = MagicMock(return_value=self)
        self.limit = MagicMock(return_value=self)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._results:
            raise StopAsyncIteration
        return self._results.pop(0)

    async def to_list(self, length=None):
        return self._results


@pytest.fixture
def mock_gadget_create() -> GadgetCreate:
    """
    Fixture to provide a test GadgetCreate instance.
    """
    return GadgetCreate(
        # id="123e4567-e89b-12d3-a456-426614174000",
        name="Test Gadget",
        height="10cm",
        mass="5kg",
        force=20,
    )


@pytest.fixture
def mock_db_gadget() -> dict:
    """
    Fixture to return a fake gadget document as it would appear in MongoDB (with 'id').
    """
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "Test Gadget",
        "height": "10cm",
        "mass": "5kg",
        "force": 20,
    }


@pytest.fixture
def mock_mongo_db(mock_db_gadget):
    """
    Fixture for a mock MongoDB database with 'gadgets' and 'gadget_zap_tasks' collections.
    """
    collection = MagicMock()
    collection.find_one = AsyncMock(return_value=mock_db_gadget.copy())
    collection.insert_one = AsyncMock(return_value=mock_db_gadget.copy())
    collection.update_one = AsyncMock(return_value=None)

    task_collection = MagicMock()

    mongo_db = {"gadgets": collection, "gadget_zap_tasks": task_collection}
    return mongo_db


async def test_gadget_create(mock_mongo_db, mock_gadget_create, mock_db_gadget):
    """
    Test creating a gadget in the repository.
    """
    fixed_id = UUID(mock_db_gadget["id"])

    with patch("app.layers.repository.v1.gadgets.uuid4", return_value=fixed_id):
        repo = GadgetRepository(db=mock_mongo_db)
        result = await repo.gadget_create(mock_gadget_create)

    assert result == GadgetRead(**mock_db_gadget)


@pytest.mark.asyncio
async def test_get_by_id_found(mock_mongo_db, mock_db_gadget):
    """
    Test retrieving a gadget by ID when it exists.
    """
    repo = GadgetRepository(db=mock_mongo_db)
    result = await repo.get_by_id(mock_db_gadget["id"])

    assert isinstance(result, GadgetRead)
    assert result.id == mock_db_gadget["id"]
    assert result.name == mock_db_gadget["name"]


@pytest.mark.asyncio
async def test_get_by_id_legacy_format(mock_mongo_db):
    """
    Test retrieving a gadget with legacy schema (gadget_id instead of id, missing name).
    """
    legacy_doc = {
        "gadget_id": "legacy-uuid-001",
        "height": "10",
        "mass": "5",
        "force": 20,
    }
    mock_mongo_db["gadgets"].find_one.return_value = legacy_doc
    repo = GadgetRepository(db=mock_mongo_db)
    result = await repo.get_by_id("legacy-uuid-001")

    assert isinstance(result, GadgetRead)
    assert result.id == "legacy-uuid-001"
    assert result.name == "Gadget (legacy-uuid-001)"
    assert result.height == "10"
    assert result.mass == "5"
    assert result.force == 20


@pytest.mark.asyncio
async def test_get_by_id_not_found(mock_mongo_db):
    """
    Test retrieving a gadget by ID when it does not exist.
    """
    # NOTE: simulate a not-found response for a different ID
    mock_mongo_db["gadgets"].find_one.return_value = None
    repo = GadgetRepository(db=mock_mongo_db)

    with pytest.raises(ResourceNotFoundError):
        await repo.get_by_id("non-existent-id")


@pytest.mark.asyncio
async def test_update_force_found(mock_mongo_db, mock_db_gadget):
    """
    Test updating the force value of a gadget when it exists.
    """
    updated_doc = mock_db_gadget.copy()
    updated_doc["force"] = 42

    mock_mongo_db["gadgets"].find_one_and_update = AsyncMock(return_value=updated_doc)

    repo = GadgetRepository(db=mock_mongo_db)
    result = await repo.update_force(
        gadget_id=updated_doc["id"],
        new_force=42,
    )

    assert result.force == 42


@pytest.mark.asyncio
async def test_update_force_not_found(mock_mongo_db, mock_db_gadget):
    """
    Test updating the force value of a gadget when it does not exist.
    """
    # Simulate no document found for update
    mock_mongo_db["gadgets"].find_one_and_update = AsyncMock(return_value=None)

    repo = GadgetRepository(db=mock_mongo_db)

    with pytest.raises(ResourceNotFoundError):
        await repo.update_force(gadget_id=mock_db_gadget["id"], new_force=42)


@pytest.mark.asyncio
async def test_get_all(mock_mongo_db, mock_db_gadget):
    """
    Test retrieving all gadgets with pagination.
    """
    doc = mock_db_gadget.copy()

    cursor = _MockAsyncCursor([doc])
    mock_mongo_db["gadgets"].find = MagicMock(return_value=cursor)
    mock_mongo_db["gadgets"].count_documents = AsyncMock(return_value=1)

    repo = GadgetRepository(db=mock_mongo_db)
    gadgets, total = await repo.get_all(page=1, page_size=10)

    assert total == 1
    assert len(gadgets) == 1
    assert isinstance(gadgets[0], GadgetRead)


@pytest.mark.asyncio
async def test_get_all_with_search(mock_mongo_db, mock_db_gadget):
    """
    Test retrieving all gadgets with a search filter.
    """
    doc = mock_db_gadget.copy()

    cursor = _MockAsyncCursor([doc])
    mock_mongo_db["gadgets"].find = MagicMock(return_value=cursor)
    mock_mongo_db["gadgets"].count_documents = AsyncMock(return_value=1)

    repo = GadgetRepository(db=mock_mongo_db)
    gadgets, total = await repo.get_all(search="Test")

    assert total == 1
    # Verify $or filter was used with search
    call_args = mock_mongo_db["gadgets"].count_documents.call_args[0][0]
    assert "$or" in call_args


@pytest.mark.asyncio
async def test_update_success(mock_mongo_db, mock_db_gadget):
    """
    Test updating a gadget when it exists.
    """
    updated_doc = mock_db_gadget.copy()
    updated_doc["name"] = "Updated"

    mock_mongo_db["gadgets"].find_one_and_update = AsyncMock(return_value=updated_doc)

    repo = GadgetRepository(db=mock_mongo_db)
    result = await repo.update(mock_db_gadget["id"], GadgetUpdate(name="Updated"))

    assert isinstance(result, GadgetRead)
    assert result.name == "Updated"


@pytest.mark.asyncio
async def test_update_not_found(mock_mongo_db, mock_db_gadget):
    """
    Test updating a gadget when it does not exist.
    """
    mock_mongo_db["gadgets"].find_one_and_update = AsyncMock(return_value=None)

    repo = GadgetRepository(db=mock_mongo_db)

    with pytest.raises(ResourceNotFoundError):
        await repo.update(mock_db_gadget["id"], GadgetUpdate(name="nope"))


@pytest.mark.asyncio
async def test_delete_success(mock_mongo_db, mock_db_gadget):
    """
    Test deleting a gadget when it exists.
    """
    mock_result = MagicMock()
    mock_result.deleted_count = 1
    mock_mongo_db["gadgets"].delete_one = AsyncMock(return_value=mock_result)

    repo = GadgetRepository(db=mock_mongo_db)
    await repo.delete(mock_db_gadget["id"])

    mock_mongo_db["gadgets"].delete_one.assert_called_once()


@pytest.mark.asyncio
async def test_delete_not_found(mock_mongo_db, mock_db_gadget):
    """
    Test deleting a gadget when it does not exist.
    """
    mock_result = MagicMock()
    mock_result.deleted_count = 0
    mock_mongo_db["gadgets"].delete_one = AsyncMock(return_value=mock_result)

    repo = GadgetRepository(db=mock_mongo_db)

    with pytest.raises(ResourceNotFoundError):
        await repo.delete("nonexistent")


@pytest.mark.asyncio
async def test_bulk_delete(mock_mongo_db):
    """
    Test bulk deleting gadgets.
    """
    mock_result = MagicMock()
    mock_result.deleted_count = 2
    mock_mongo_db["gadgets"].delete_many = AsyncMock(return_value=mock_result)

    repo = GadgetRepository(db=mock_mongo_db)
    count = await repo.bulk_delete(["g1", "g2"])

    assert count == 2


@pytest.mark.asyncio
async def test_bulk_update(mock_mongo_db):
    """
    Test bulk updating gadgets.
    """
    mock_result = MagicMock()
    mock_result.modified_count = 3
    mock_mongo_db["gadgets"].update_many = AsyncMock(return_value=mock_result)

    repo = GadgetRepository(db=mock_mongo_db)
    count = await repo.bulk_update(["g1", "g2", "g3"], GadgetUpdate(name="bulk"))

    assert count == 3


@pytest.mark.asyncio
async def test_bulk_update_no_fields(mock_mongo_db):
    """
    Test bulk update with no fields returns 0 without DB call.
    """
    repo = GadgetRepository(db=mock_mongo_db)
    count = await repo.bulk_update(["g1"], GadgetUpdate())

    assert count == 0


@pytest.mark.asyncio
async def test_zap_task_create(mock_mongo_db):
    """Test creating a gadget zap task document in the task collection."""
    from uuid import uuid4

    insert_result = MagicMock()
    insert_result.inserted_id = "new-id-123"
    mock_mongo_db["gadget_zap_tasks"].insert_one = AsyncMock(return_value=insert_result)

    repo = GadgetRepository(db=mock_mongo_db)
    task_uuid = uuid4()
    gadget_id = "123e4567-e89b-12d3-a456-426614174000"

    result = await repo.zap_task_create(
        gadget_id=gadget_id,
        task_uuid=str(task_uuid),
        duration=5,
    )

    mock_mongo_db["gadget_zap_tasks"].insert_one.assert_called_once()
    insert_doc = mock_mongo_db["gadget_zap_tasks"].insert_one.call_args[0][0]
    assert insert_doc["gadget_id"] == gadget_id
    assert insert_doc["task_uuid"] == str(task_uuid)
    assert insert_doc["state"] == "PENDING"
    assert insert_doc["duration"] == 5

    assert isinstance(result, GadgetZapTaskRecord)
    assert result.gadget_id == gadget_id
    assert str(result.task_uuid) == str(task_uuid)
    assert result.state == "PENDING"
    assert result.id == "new-id-123"


@pytest.mark.asyncio
async def test_zap_task_update(mock_mongo_db):
    """Test updating a gadget zap task document in the task collection."""
    from uuid import uuid4

    repo = GadgetRepository(db=mock_mongo_db)
    task_uuid = uuid4()

    mock_mongo_db["gadget_zap_tasks"].find_one_and_update = AsyncMock(
        return_value={
            "gadget_id": "123e4567-e89b-12d3-a456-426614174000",
            "task_uuid": str(task_uuid),
            "state": "RUNNING",
            "created_at": "2026-06-20T01:00:00Z",
        }
    )

    result = await repo.zap_task_update(
        task_uuid=str(task_uuid),
        state="RUNNING",
    )

    mock_mongo_db["gadget_zap_tasks"].find_one_and_update.assert_called_once()
    filter_doc = mock_mongo_db["gadget_zap_tasks"].find_one_and_update.call_args[0][0]
    assert filter_doc["task_uuid"] == str(task_uuid)

    assert isinstance(result, GadgetZapTaskRecord)
    assert result.state == "RUNNING"


@pytest.mark.asyncio
async def test_zap_task_update_not_found(mock_mongo_db):
    """Test zap_task_update raises ResourceNotFoundError when task does not exist."""
    from uuid import uuid4

    repo = GadgetRepository(db=mock_mongo_db)
    task_uuid = uuid4()

    mock_mongo_db["gadget_zap_tasks"].find_one_and_update = AsyncMock(return_value=None)

    with pytest.raises(ResourceNotFoundError):
        await repo.zap_task_update(task_uuid=str(task_uuid), state="RUNNING")


@pytest.mark.asyncio
async def test_zap_task_list(mock_mongo_db):
    """Test listing zap tasks for a gadget with pagination."""
    from uuid import uuid4

    repo = GadgetRepository(db=mock_mongo_db)
    gadget_id = "123e4567-e89b-12d3-a456-426614174000"

    task_uuid_1 = uuid4()
    task_uuid_2 = uuid4()

    docs = [
        {
            "gadget_id": gadget_id,
            "task_uuid": str(task_uuid_1),
            "state": "SUCCESS",
            "created_at": "2026-06-20T01:00:00Z",
        },
        {
            "gadget_id": gadget_id,
            "task_uuid": str(task_uuid_2),
            "state": "PENDING",
            "created_at": "2026-06-20T02:00:00Z",
        },
    ]

    mock_mongo_db["gadget_zap_tasks"].count_documents = AsyncMock(return_value=2)

    cursor = _MockAsyncCursor(docs)
    mock_mongo_db["gadget_zap_tasks"].find = MagicMock(return_value=cursor)

    tasks, total = await repo.zap_task_list(gadget_id=gadget_id, page=1, page_size=10)

    assert total == 2
    assert len(tasks) == 2
    assert isinstance(tasks[0], GadgetZapTaskRecord)
    assert tasks[0].state == "SUCCESS"


@pytest.mark.asyncio
async def test_zap_task_list_empty(mock_mongo_db):
    """Test listing zap tasks when none exist for a gadget."""
    repo = GadgetRepository(db=mock_mongo_db)
    gadget_id = "nonexistent"

    mock_mongo_db["gadget_zap_tasks"].count_documents = AsyncMock(return_value=0)

    cursor = _MockAsyncCursor([])
    mock_mongo_db["gadget_zap_tasks"].find = MagicMock(return_value=cursor)

    tasks, total = await repo.zap_task_list(gadget_id=gadget_id, page=1, page_size=10)

    assert total == 0
    assert len(tasks) == 0


@pytest.mark.asyncio
async def test_get_zap_task_by_uuid_found(mock_mongo_db):
    """Test retrieving a zap task by UUID scoped to a gadget."""
    repo = GadgetRepository(db=mock_mongo_db)
    gadget_id = "123e4567-e89b-12d3-a456-426614174000"
    task_uuid = "test-task-uuid-123"

    mock_mongo_db["gadget_zap_tasks"].find_one = AsyncMock(
        return_value={
            "task_uuid": task_uuid,
            "gadget_id": gadget_id,
            "state": "SUCCESS",
            "duration": 5,
            "runtime": 4,
            "result": {"gadget_id": gadget_id, "new_force": 21},
        }
    )

    result = await repo.get_zap_task_by_uuid(gadget_id, task_uuid)

    mock_mongo_db["gadget_zap_tasks"].find_one.assert_called_once_with(
        {"gadget_id": gadget_id, "task_uuid": task_uuid}
    )
    assert result is not None
    assert result["task_uuid"] == task_uuid
    assert result["state"] == "SUCCESS"


@pytest.mark.asyncio
async def test_get_zap_task_by_uuid_not_found(mock_mongo_db):
    """Test get_zap_task_by_uuid returns None when task does not exist."""
    repo = GadgetRepository(db=mock_mongo_db)
    task_uuid = "non-existent-uuid"

    mock_mongo_db["gadget_zap_tasks"].find_one = AsyncMock(return_value=None)

    result = await repo.get_zap_task_by_uuid("nonexistent", task_uuid)

    assert result is None


@pytest.mark.asyncio
async def test_zap_task_list_with_search(mock_mongo_db):
    """Test listing zap tasks with a search filter that uses $or."""
    from uuid import uuid4

    repo = GadgetRepository(db=mock_mongo_db)
    gadget_id = "123e4567-e89b-12d3-a456-426614174000"

    task_uuid_1 = uuid4()

    docs = [
        {
            "gadget_id": gadget_id,
            "task_uuid": str(task_uuid_1),
            "state": "SUCCESS",
            "created_at": "2026-06-20T01:00:00Z",
        },
    ]

    mock_mongo_db["gadget_zap_tasks"].count_documents = AsyncMock(return_value=1)

    cursor = _MockAsyncCursor(docs)
    mock_mongo_db["gadget_zap_tasks"].find = MagicMock(return_value=cursor)

    tasks, total = await repo.zap_task_list(
        gadget_id=gadget_id, search="abc123", page=1, page_size=10
    )

    assert total == 1
    assert len(tasks) == 1
    assert isinstance(tasks[0], GadgetZapTaskRecord)

    count_call = mock_mongo_db["gadget_zap_tasks"].count_documents.call_args[0][0]
    assert "gadget_id" in count_call
    assert count_call["gadget_id"] == gadget_id
    assert "$or" in count_call
    assert {"task_uuid": {"$regex": "abc123", "$options": "i"}} in count_call["$or"]
    assert {"state": {"$regex": "abc123", "$options": "i"}} in count_call["$or"]

    find_call = mock_mongo_db["gadget_zap_tasks"].find.call_args[0][0]
    assert "gadget_id" in find_call
    assert find_call["gadget_id"] == gadget_id
    assert "$or" in find_call
