# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for service/domain layer."""

import contextlib
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from nmtfast.auth.v1.exceptions import AuthorizationError
from nmtfast.settings.v1.schemas import SectionACL

from app.core.v1.settings import AppSettings
from app.errors.v1.exceptions import NotFoundError
from app.schemas.v1.widgets import WidgetCreate, WidgetRead, WidgetZap, WidgetZapTask
from app.services.v1.widgets import WidgetService


@pytest.mark.asyncio
async def test_widget_create(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_widget_create: WidgetCreate,
    mock_widget_read: WidgetRead,
):
    """Test successful creation of a widget."""

    service = WidgetService(mock_widget_repository, mock_allow_acls, mock_settings)
    mock_widget_repository.widget_create = AsyncMock(return_value=mock_widget_read)
    result = await service.widget_create(mock_widget_create)

    mock_widget_repository.widget_create.assert_called_once()
    assert isinstance(result, WidgetRead)
    assert result.name == mock_widget_read.name


@pytest.mark.asyncio
async def test_widget_create_authorization_error(
    mock_widget_repository: AsyncMock,
    mock_deny_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_widget_create: WidgetCreate,
):
    """Test authorization error during widget creation."""

    service = WidgetService(mock_widget_repository, mock_deny_acls, mock_settings)

    with pytest.raises(AuthorizationError):
        await service.widget_create(mock_widget_create)

    # raising the exception is all that needs to be tested


@pytest.mark.asyncio
async def test_widget_get_by_id_success(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_widget_read: WidgetRead,
):
    """Test successful retrieval of a widget by ID."""

    service = WidgetService(mock_widget_repository, mock_allow_acls, mock_settings)
    mock_widget_repository.get_by_id = AsyncMock(return_value=mock_widget_read)
    result = await service.widget_get_by_id(mock_widget_read.id)

    mock_widget_repository.get_by_id.assert_called_once()
    assert isinstance(result, WidgetRead)
    assert result.id == mock_widget_read.id


@pytest.mark.asyncio
async def test_widget_get_by_id_not_found(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
):
    """Test NotFoundError when retrieving a non-existent widget by ID."""

    service = WidgetService(mock_widget_repository, mock_allow_acls, mock_settings)
    mock_widget_repository.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await service.widget_get_by_id(123)

    # raising the exception is all that needs to be tested


@pytest.mark.asyncio
async def test_widget_get_by_id_authorization_error(
    mock_widget_repository: AsyncMock,
    mock_deny_acls: list[SectionACL],
    mock_settings: AppSettings,
):
    """Test authorization error during widget retrieval."""

    service = WidgetService(mock_widget_repository, mock_deny_acls, mock_settings)

    with pytest.raises(AuthorizationError):
        await service.widget_get_by_id(123)

    # raising the exception is all that needs to be tested


@pytest.mark.asyncio
async def test_widget_zap_success(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_widget_read: WidgetRead,
    mock_widget_zap: WidgetZap,
    mock_widget_zap_task: WidgetZapTask,
):
    """Test successful zapping of a widget."""

    service = WidgetService(mock_widget_repository, mock_allow_acls, mock_settings)
    mock_widget_repository.get_by_id = AsyncMock(return_value=mock_widget_read)

    mock_async_result = MagicMock()
    mock_async_result.task.id = "test-uuid"
    mock_widget_zap_task_func = MagicMock(return_value=mock_async_result)

    with contextlib.ExitStack() as stack:
        mock_zap_task = stack.enter_context(
            patch("app.services.v1.widgets.widget_zap_task", mock_widget_zap_task_func)
        )
        mock_store_metadata = stack.enter_context(
            patch("app.services.v1.widgets.store_task_metadata")
        )
        result = await service.widget_zap(mock_widget_read.id, mock_widget_zap)

        mock_widget_repository.get_by_id.assert_called_once_with(mock_widget_read.id)
        mock_zap_task.assert_called_once()
        mock_store_metadata.assert_called_once_with(
            ANY,  # huey_app
            "test-uuid",
            {
                "uuid": "test-uuid",
                "id": mock_widget_read.id,
                "state": "PENDING",
                "duration": mock_widget_zap.duration,
                "runtime": 0,
            },
        )
        assert isinstance(result, WidgetZapTask)
        assert result.uuid == "test-uuid"
        assert result.id == mock_widget_read.id
        assert result.duration == mock_widget_zap.duration


@pytest.mark.asyncio
async def test_widget_zap_not_found(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
):
    """Test NotFoundError when attempting to zap a non-existent widget."""

    service = WidgetService(mock_widget_repository, mock_allow_acls, mock_settings)
    mock_widget_repository.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await service.widget_zap(
            widget_id=123,
            payload={"duration": 1},
        )

    # raising the exception is all that needs to be tested


@pytest.mark.asyncio
async def test_widget_zap_by_uuid_not_found_task(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_widget_read: WidgetRead,
):
    """Test NotFoundError when the zap task metadata is not found."""

    service = WidgetService(mock_widget_repository, mock_allow_acls, mock_settings)
    mock_widget_repository.get_by_id = AsyncMock(return_value=mock_widget_read)

    with contextlib.ExitStack() as stack:
        mock_fetch_result = stack.enter_context(
            patch("app.services.v1.widgets.fetch_task_result", return_value=None)
        )
        mock_fetch_metadata = stack.enter_context(
            patch("app.services.v1.widgets.fetch_task_metadata", return_value=None)
        )

        with pytest.raises(NotFoundError, match="Task"):
            await service.widget_zap_by_uuid(mock_widget_read.id, "non-existent-uuid")

        mock_widget_repository.get_by_id.assert_called_once_with(mock_widget_read.id)
        mock_fetch_result.assert_called_once_with(ANY, "non-existent-uuid")
        mock_fetch_metadata.assert_called_once_with(ANY, "non-existent-uuid")


@pytest.mark.asyncio
async def test_widget_zap_by_uuid_returns_task_result(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_widget_read: WidgetRead,
    mock_widget_zap_task: WidgetZapTask,
):
    """Test that widget_zap_by_uuid returns task_result when it's available."""

    service = WidgetService(mock_widget_repository, mock_allow_acls, mock_settings)
    mock_widget_repository.get_by_id = AsyncMock(return_value=mock_widget_read)

    with contextlib.ExitStack() as stack:
        mock_fetch_result = stack.enter_context(
            patch(
                "app.services.v1.widgets.fetch_task_result",
                return_value=mock_widget_zap_task.model_dump(),
            )
        )
        mock_fetch_metadata = stack.enter_context(
            patch("app.services.v1.widgets.fetch_task_metadata")
        )
        result = await service.widget_zap_by_uuid(mock_widget_read.id, "test-uuid")

        mock_widget_repository.get_by_id.assert_called_once_with(mock_widget_read.id)
        mock_fetch_result.assert_called_once_with(ANY, "test-uuid")
        mock_fetch_metadata.assert_not_called()
        assert isinstance(result, WidgetZapTask)
        assert result.uuid == "test-uuid"
        assert result.id == mock_widget_read.id
        assert result.state == "PENDING"
        assert result.duration == 5
        assert result.runtime == 0


@pytest.mark.asyncio
async def test_widget_zap_by_uuid_not_found(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
):
    """Test NotFoundError when attempting to zap a non-existent widget."""

    service = WidgetService(mock_widget_repository, mock_allow_acls, mock_settings)
    mock_widget_repository.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await service.widget_zap_by_uuid(
            widget_id=123,
            task_uuid="not-a-real-uuid",
        )

    # raising the exception is all that needs to be tested
