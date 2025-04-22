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
def mock_widget():
    """
    Fixture for a mock Widget object.
    """
    widget = Widget(id=1, name="Test Widget", force=10)

    return widget


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
