# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""pytest fixtures for unit / integration tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.v1.widgets import Widget
from app.schemas.v1.gadgets import GadgetCreate
from app.schemas.v1.widgets import WidgetCreate


@pytest.fixture
def mock_async_session() -> AsyncMock:
    """
    Fixture to provide a mock AsyncSession.
    """
    return AsyncMock(spec=AsyncSession)


#
# widget fixtures
#


@pytest.fixture
def mock_widget_create() -> WidgetCreate:
    """
    Fixture to provide a test WidgetCreate instance.
    """
    return WidgetCreate(name="Test Widget")


@pytest.fixture
def mock_db_widget():
    """
    Fixture to create a mock Widget database object.
    """
    return Widget(id=1, name="Test Widget", height="10cm", mass="5kg", force=20)


#
# gadget fixtures
#

# @pytest.fixture
# def mock_gadget():
#     """
#     Fixture for a mock gadget dict (as stored in MongoDB).
#     """
#     return {
#         "id": "id-1",
#         "name": "ZapBot 5000",
#         "force": 5,
#     }


@pytest.fixture
def mock_gadget_create() -> GadgetCreate:
    """
    Fixture to provide a test GadgetCreate instance.
    """
    return GadgetCreate(
        id="123e4567-e89b-12d3-a456-426614174000",
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


# @pytest.fixture
# def mock_mongo_collection() -> AsyncMock:
#     """
#     Fixture to provide a mock AsyncIOMotorCollection.
#     """
#     return AsyncMock(spec=AsyncIOMotorCollection)


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
