# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""pytest fixtures for unit / integration tests."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.v1.widgets import Widget
from app.schemas.v1.widgets import WidgetCreate


@pytest.fixture
def mock_async_session() -> AsyncMock:
    """
    Fixture to provide a mock AsyncSession.
    """
    return AsyncMock(spec=AsyncSession)


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
