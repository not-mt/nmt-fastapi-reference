# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for repository layer using MongoDB."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.errors.v1.exceptions import ResourceNotFoundError
from app.layers.repository.v1.gadgets import GadgetRepository
from app.schemas.dto.v1.gadgets import GadgetCreate, GadgetRead, GadgetUpdate


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
    Fixture for a mock MongoDB database with a 'gadgets' collection using AsyncMock.
    """
    collection = MagicMock()
    collection.find_one = AsyncMock(return_value=mock_db_gadget.copy())
    collection.insert_one = AsyncMock(return_value=mock_db_gadget.copy())
    collection.update_one = AsyncMock(return_value=None)

    mongo_db = {"gadgets": collection}
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
