# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for repository layer."""

from unittest.mock import AsyncMock

import pytest

from app.models.v1.widgets import Widget
from app.repositories.v1.widgets import WidgetRepository
from app.schemas.v1.widgets import WidgetCreate


@pytest.mark.asyncio
async def test_create_widget(
    mock_async_session: AsyncMock,
    mock_widget_create: WidgetCreate,
):
    """Test creating a widget in the repository."""

    repository = WidgetRepository(mock_async_session)
    mock_async_session.add.return_value = None
    mock_async_session.commit.return_value = None
    mock_async_session.refresh.return_value = None

    # NOTE: simulate assigning an 'id' to the object, without actually needing an
    #   underlying DB to do this for us, because this is a unit test
    mock_async_session.add.side_effect = lambda db_widget: setattr(db_widget, "id", 1)
    result = await repository.create_widget(mock_widget_create)

    mock_async_session.add.assert_called_once()
    mock_async_session.commit.assert_called_once()
    mock_async_session.refresh.assert_called_once()

    assert isinstance(result, Widget)
    assert result.name == mock_widget_create.name


@pytest.mark.asyncio
async def test_get_widget_by_id_found(
    mock_async_session: AsyncMock,
    mock_db_widget: Widget,
):
    """Test retrieving a widget by ID when it exists."""

    repository = WidgetRepository(mock_async_session)
    mock_async_session.get.return_value = mock_db_widget

    result = await repository.get_by_id(mock_db_widget.id)

    mock_async_session.get.assert_called_once_with(Widget, mock_db_widget.id)
    assert result == mock_db_widget


@pytest.mark.asyncio
async def test_get_widget_by_id_not_found(mock_async_session: AsyncMock):
    """Test retrieving a widget by ID when it does not exist."""

    repository = WidgetRepository(mock_async_session)
    mock_async_session.get.return_value = None

    result = await repository.get_by_id(123)

    mock_async_session.get.assert_called_once_with(Widget, 123)
    assert result is None
