# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for service/domain layer."""

from unittest.mock import AsyncMock

import pytest
from nmtfast.auth.v1.exceptions import AuthorizationError
from nmtfast.settings.v1.schemas import SectionACL

from app.core.v1.settings import AppSettings
from app.errors.v1.exceptions import NotFoundError
from app.schemas.v1.widgets import WidgetCreate, WidgetRead
from app.services.v1.widgets import WidgetService


@pytest.mark.asyncio
async def test_create_widget(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_widget_create: WidgetCreate,
    mock_widget_read: WidgetRead,
):
    """Test successful creation of a widget."""

    service = WidgetService(mock_widget_repository, mock_allow_acls, mock_settings)
    mock_widget_repository.create_widget = AsyncMock(return_value=mock_widget_read)
    result = await service.create_widget(mock_widget_create)

    mock_widget_repository.create_widget.assert_called_once()
    assert isinstance(result, WidgetRead)
    assert result.name == mock_widget_read.name


@pytest.mark.asyncio
async def test_create_widget_authorization_error(
    mock_widget_repository: AsyncMock,
    mock_deny_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_widget_create: WidgetCreate,
):
    """Test authorization error during widget creation."""

    service = WidgetService(mock_widget_repository, mock_deny_acls, mock_settings)

    with pytest.raises(AuthorizationError):
        await service.create_widget(mock_widget_create)

    # raising the exception is all that needs to be tested


@pytest.mark.asyncio
async def test_get_widget_by_id_success(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_widget_read: WidgetRead,
):
    """Test successful retrieval of a widget by ID."""

    service = WidgetService(mock_widget_repository, mock_allow_acls, mock_settings)
    mock_widget_repository.get_by_id = AsyncMock(return_value=mock_widget_read)
    result = await service.get_widget_by_id(mock_widget_read.id)

    mock_widget_repository.get_by_id.assert_called_once()
    assert isinstance(result, WidgetRead)
    assert result.id == mock_widget_read.id


@pytest.mark.asyncio
async def test_get_widget_by_id_not_found(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
):
    """Test NotFoundError when retrieving a non-existent widget by ID."""

    service = WidgetService(mock_widget_repository, mock_allow_acls, mock_settings)
    mock_widget_repository.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await service.get_widget_by_id(123)

    # raising the exception is all that needs to be tested


@pytest.mark.asyncio
async def test_get_widget_by_id_authorization_error(
    mock_widget_repository: AsyncMock,
    mock_deny_acls: list[SectionACL],
    mock_settings: AppSettings,
):
    """Test authorization error during widget retrieval."""

    service = WidgetService(mock_widget_repository, mock_deny_acls, mock_settings)

    with pytest.raises(AuthorizationError):
        await service.get_widget_by_id(123)

    # raising the exception is all that needs to be tested
