# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for service/domain layer."""

import contextlib
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from nmtfast.auth.v1.exceptions import AuthorizationError
from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.settings.v1.schemas import SectionACL
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.v1.settings import AppSettings
from app.errors.v1.exceptions import ResourceNotFoundError
from app.models.v1.widgets import Widget
from app.repositories.v1.widgets import WidgetRepository
from app.schemas.v1.widgets import WidgetCreate, WidgetRead, WidgetZap, WidgetZapTask
from app.services.v1.widgets import WidgetService


@pytest.fixture
def mock_cache():
    """
    Fixture to return a mock AppCacheBase.
    """
    return AsyncMock(spec=AppCacheBase)


@pytest.fixture
def mock_async_session() -> AsyncMock:
    """
    Fixture to provide a mock AsyncSession.
    """
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_widget_repository(mock_async_session: AsyncMock) -> WidgetRepository:
    """
    Fixture to provide a mock WidgetRepository.
    """
    return WidgetRepository(mock_async_session)


@pytest.fixture
def mock_widget_create() -> WidgetCreate:
    """
    Fixture to provide a test WidgetCreate instance.
    """
    return WidgetCreate(name="Test Widget")


@pytest.fixture
def mock_widget_read() -> WidgetRead:
    """
    Fixture to provide a test WidgetRead instance.
    """
    return WidgetRead(id=1, name="Test Widget", height="10", mass="5", force=20)


@pytest.fixture
def mock_widget_zap() -> WidgetZap:
    """
    Fixture for a sample WidgetZap payload.
    """
    return WidgetZap(duration=5)


@pytest.fixture
def mock_widget_zap_task() -> WidgetZapTask:
    """
    Fixture for a sample WidgetZapTask.
    """
    return WidgetZapTask(uuid="test-uuid", id=1, state="PENDING", duration=5, runtime=0)


@pytest.fixture
def mock_db_widget() -> Widget:
    """
    Fixture to provide a test Widget ADO instance.
    """
    return Widget(name="Test Widget", id="123")


@pytest.mark.asyncio
async def test_widget_create(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_widget_create: WidgetCreate,
    mock_widget_read: WidgetRead,
):
    """
    Test successful creation of a widget.
    """
    service = WidgetService(
        mock_widget_repository, mock_allow_acls, mock_settings, mock_cache
    )
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
    mock_cache: AppCacheBase,
    mock_widget_create: WidgetCreate,
):
    """
    Test authorization error during widget creation.
    """
    service = WidgetService(
        mock_widget_repository, mock_deny_acls, mock_settings, mock_cache
    )

    with pytest.raises(AuthorizationError):
        await service.widget_create(mock_widget_create)

    # raising the exception is all that needs to be tested


@pytest.mark.asyncio
async def test_widget_get_by_id_success(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_widget_read: WidgetRead,
):
    """
    Test successful retrieval of a widget by ID.
    """

    service = WidgetService(
        mock_widget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_widget_repository.get_by_id = AsyncMock(return_value=mock_widget_read)
    result = await service.widget_get_by_id(mock_widget_read.id)

    mock_widget_repository.get_by_id.assert_called_once()
    assert isinstance(result, WidgetRead)
    assert result.id == mock_widget_read.id


@pytest.mark.asyncio
async def test_widget_get_by_id_authorization_error(
    mock_widget_repository: AsyncMock,
    mock_deny_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
):
    """
    Test authorization error during widget retrieval.
    """
    service = WidgetService(
        mock_widget_repository, mock_deny_acls, mock_settings, mock_cache
    )

    with pytest.raises(AuthorizationError):
        await service.widget_get_by_id(123)

    # raising the exception is all that needs to be tested


@pytest.mark.asyncio
async def test_widget_zap_success(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_widget_read: WidgetRead,
    mock_widget_zap: WidgetZap,
    mock_widget_zap_task: WidgetZapTask,
):
    """
    Test successful zapping of a widget.
    """
    service = WidgetService(
        mock_widget_repository, mock_allow_acls, mock_settings, mock_cache
    )
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
async def test_widget_zap_by_uuid_not_found_task(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_widget_read: WidgetRead,
):
    """
    Test ResourceNotFoundError when the zap task metadata is not found.
    """
    service = WidgetService(
        mock_widget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_widget_repository.get_by_id = AsyncMock(return_value=mock_widget_read)

    with contextlib.ExitStack() as stack:
        mock_fetch_result = stack.enter_context(
            patch("app.services.v1.widgets.fetch_task_result", return_value=None)
        )
        mock_fetch_metadata = stack.enter_context(
            patch("app.services.v1.widgets.fetch_task_metadata", return_value=None)
        )

        with pytest.raises(ResourceNotFoundError, match="Task"):
            await service.widget_zap_by_uuid(mock_widget_read.id, "non-existent-uuid")

        mock_widget_repository.get_by_id.assert_called_once_with(mock_widget_read.id)
        mock_fetch_result.assert_called_once_with(ANY, "non-existent-uuid")
        mock_fetch_metadata.assert_called_once_with(ANY, "non-existent-uuid")


@pytest.mark.asyncio
async def test_widget_zap_by_uuid_returns_task_result(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_widget_read: WidgetRead,
    mock_widget_zap_task: WidgetZapTask,
):
    """
    Test that widget_zap_by_uuid returns task_result when it's available.
    """
    service = WidgetService(
        mock_widget_repository, mock_allow_acls, mock_settings, mock_cache
    )
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
    mock_cache: AppCacheBase,
    mock_db_widget: Widget,
):
    """
    Test ResourceNotFoundError when attempting to zap a non-existent widget.
    """
    service = WidgetService(
        mock_widget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_widget_repository.get_by_id = AsyncMock(return_value=mock_db_widget)

    with pytest.raises(ResourceNotFoundError):
        await service.widget_zap_by_uuid(
            widget_id=123,
            task_uuid="not-a-real-uuid",
        )

    # raising the exception is all that needs to be tested
