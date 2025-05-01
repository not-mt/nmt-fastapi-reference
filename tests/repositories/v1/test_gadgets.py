# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for repository layer using MongoDB."""

from unittest.mock import patch
from uuid import UUID

import pytest

from app.repositories.v1.gadgets import GadgetRepository
from app.schemas.v1.gadgets import GadgetRead


async def test_gadget_create(mock_mongo_db, mock_gadget_create, mock_db_gadget):
    """
    Test creating a gadget in the repository.
    """
    fixed_id = UUID(mock_db_gadget["id"])

    with patch("app.repositories.v1.gadgets.uuid4", return_value=fixed_id):
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

    result = await repo.get_by_id("non-existent-id")

    assert result is None
