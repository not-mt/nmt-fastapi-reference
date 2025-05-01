# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""pytest fixtures for unit / integration tests."""

import uuid
from unittest.mock import MagicMock

import pytest
from huey.api import Task

from app.models.v1.widgets import Widget


@pytest.fixture
def mock_gadget():
    """
    Fixture for a mock gadget dict (as stored in MongoDB).
    """
    return {
        "id": "id-1",
        "name": "ZapBot 5000",
        "force": 5,
    }


@pytest.fixture
def mock_widget():
    """
    Fixture for a mock widget.
    """
    return Widget(id=1, name="Test Widget", force=10)


@pytest.fixture
def mock_task():
    """
    Fixture for a mock Huey Task object.
    """
    task = MagicMock(spec=Task)
    task.id = str(uuid.uuid4())

    return task


@pytest.fixture
def mock_db_session(mock_widget):
    """
    Fixture for a mock SQLAlchemy session.
    """
    session = MagicMock()
    session.get.return_value = mock_widget
    session.commit.return_value = None

    return session


@pytest.fixture
def mock_mongo_db(mock_gadget):
    """
    Fixture for a mock MongoDB database with a 'gadgets' collection.
    """
    collection = MagicMock()
    collection.find_one.return_value = mock_gadget.copy()
    collection.update_one.return_value = None
    mongo_db = {"gadgets": collection}

    return mongo_db
