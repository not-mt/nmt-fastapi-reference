# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for repository layer."""

from unittest.mock import AsyncMock

import pytest

from app.models.v1.gadgets import Gadget
from app.repositories.v1.gadgets import GadgetRepository
from app.schemas.v1.gadgets import GadgetCreate


@pytest.mark.asyncio
async def test_gadget_create(
    mock_async_session: AsyncMock,
    mock_gadget_create: GadgetCreate,
):
    """Test creating a gadget in the repository."""

    repository = GadgetRepository(mock_async_session)
    mock_async_session.add.return_value = None
    mock_async_session.commit.return_value = None
    mock_async_session.refresh.return_value = None

    # NOTE: simulate assigning an 'id' to the object, without actually needing an
    #   underlying DB to do this for us, because this is a unit test
    mock_async_session.add.side_effect = lambda db_gadget: setattr(db_gadget, "id", 1)
    result = await repository.gadget_create(mock_gadget_create)

    mock_async_session.add.assert_called_once()
    mock_async_session.commit.assert_called_once()
    mock_async_session.refresh.assert_called_once()

    assert isinstance(result, Gadget)
    assert result.name == mock_gadget_create.name


@pytest.mark.asyncio
async def test_gadget_get_by_id_found(
    mock_async_session: AsyncMock,
    mock_db_gadget: Gadget,
):
    """Test retrieving a gadget by ID when it exists."""

    repository = GadgetRepository(mock_async_session)
    mock_async_session.get.return_value = mock_db_gadget

    result = await repository.get_by_id(mock_db_gadget.id)

    mock_async_session.get.assert_called_once_with(Gadget, mock_db_gadget.id)
    assert result == mock_db_gadget


@pytest.mark.asyncio
async def test_gadget_get_by_id_not_found(mock_async_session: AsyncMock):
    """Test retrieving a gadget by ID when it does not exist."""

    repository = GadgetRepository(mock_async_session)
    mock_async_session.get.return_value = None

    result = await repository.get_by_id(123)

    mock_async_session.get.assert_called_once_with(Gadget, 123)
    assert result is None
