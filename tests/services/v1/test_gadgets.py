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
from app.schemas.v1.gadgets import GadgetCreate, GadgetRead, GadgetZap, GadgetZapTask
from app.services.v1.gadgets import GadgetService


@pytest.mark.asyncio
async def test_gadget_create(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_gadget_create: GadgetCreate,
    mock_gadget_read: GadgetRead,
):
    """Test successful creation of a gadget."""

    service = GadgetService(mock_gadget_repository, mock_allow_acls, mock_settings)
    mock_gadget_repository.gadget_create = AsyncMock(return_value=mock_gadget_read)
    result = await service.gadget_create(mock_gadget_create)

    mock_gadget_repository.gadget_create.assert_called_once()
    assert isinstance(result, GadgetRead)
    assert result.name == mock_gadget_read.name


@pytest.mark.asyncio
async def test_gadget_create_authorization_error(
    mock_gadget_repository: AsyncMock,
    mock_deny_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_gadget_create: GadgetCreate,
):
    """Test authorization error during gadget creation."""

    service = GadgetService(mock_gadget_repository, mock_deny_acls, mock_settings)

    with pytest.raises(AuthorizationError):
        await service.gadget_create(mock_gadget_create)

    # raising the exception is all that needs to be tested


@pytest.mark.asyncio
async def test_gadget_get_by_id_success(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_gadget_read: GadgetRead,
):
    """Test successful retrieval of a gadget by ID."""

    service = GadgetService(mock_gadget_repository, mock_allow_acls, mock_settings)
    mock_gadget_repository.get_by_id = AsyncMock(return_value=mock_gadget_read)
    result = await service.gadget_get_by_id(mock_gadget_read.id)

    mock_gadget_repository.get_by_id.assert_called_once()
    assert isinstance(result, GadgetRead)
    assert result.id == mock_gadget_read.id


@pytest.mark.asyncio
async def test_gadget_get_by_id_not_found(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
):
    """Test NotFoundError when retrieving a non-existent gadget by ID."""

    service = GadgetService(mock_gadget_repository, mock_allow_acls, mock_settings)
    mock_gadget_repository.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await service.gadget_get_by_id(123)

    # raising the exception is all that needs to be tested


@pytest.mark.asyncio
async def test_gadget_get_by_id_authorization_error(
    mock_gadget_repository: AsyncMock,
    mock_deny_acls: list[SectionACL],
    mock_settings: AppSettings,
):
    """Test authorization error during gadget retrieval."""

    service = GadgetService(mock_gadget_repository, mock_deny_acls, mock_settings)

    with pytest.raises(AuthorizationError):
        await service.gadget_get_by_id(123)

    # raising the exception is all that needs to be tested


@pytest.mark.asyncio
async def test_gadget_zap_success(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_gadget_read: GadgetRead,
    mock_gadget_zap: GadgetZap,
    mock_gadget_zap_task: GadgetZapTask,
):
    """Test successful zapping of a gadget."""

    service = GadgetService(mock_gadget_repository, mock_allow_acls, mock_settings)
    mock_gadget_repository.get_by_id = AsyncMock(return_value=mock_gadget_read)

    mock_async_result = MagicMock()
    mock_async_result.task.id = "test-uuid"
    mock_gadget_zap_task_func = MagicMock(return_value=mock_async_result)

    with contextlib.ExitStack() as stack:
        mock_zap_task = stack.enter_context(
            patch("app.services.v1.gadgets.gadget_zap_task", mock_gadget_zap_task_func)
        )
        mock_store_metadata = stack.enter_context(
            patch("app.services.v1.gadgets.store_task_metadata")
        )
        result = await service.gadget_zap(mock_gadget_read.id, mock_gadget_zap)

        mock_gadget_repository.get_by_id.assert_called_once_with(mock_gadget_read.id)
        mock_zap_task.assert_called_once()
        mock_store_metadata.assert_called_once_with(
            ANY,  # huey_app
            "test-uuid",
            {
                "uuid": "test-uuid",
                "id": mock_gadget_read.id,
                "state": "PENDING",
                "duration": mock_gadget_zap.duration,
                "runtime": 0,
            },
        )
        assert isinstance(result, GadgetZapTask)
        assert result.uuid == "test-uuid"
        assert result.id == mock_gadget_read.id
        assert result.duration == mock_gadget_zap.duration


@pytest.mark.asyncio
async def test_gadget_zap_not_found(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
):
    """Test NotFoundError when attempting to zap a non-existent gadget."""

    service = GadgetService(mock_gadget_repository, mock_allow_acls, mock_settings)
    mock_gadget_repository.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await service.gadget_zap(
            gadget_id=123,
            payload={"duration": 1},
        )

    # raising the exception is all that needs to be tested


@pytest.mark.asyncio
async def test_gadget_zap_by_uuid_not_found_task(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_gadget_read: GadgetRead,
):
    """Test NotFoundError when the zap task metadata is not found."""

    service = GadgetService(mock_gadget_repository, mock_allow_acls, mock_settings)
    mock_gadget_repository.get_by_id = AsyncMock(return_value=mock_gadget_read)

    with contextlib.ExitStack() as stack:
        mock_fetch_result = stack.enter_context(
            patch("app.services.v1.gadgets.fetch_task_result", return_value=None)
        )
        mock_fetch_metadata = stack.enter_context(
            patch("app.services.v1.gadgets.fetch_task_metadata", return_value=None)
        )

        with pytest.raises(NotFoundError, match="Task"):
            await service.gadget_zap_by_uuid(mock_gadget_read.id, "non-existent-uuid")

        mock_gadget_repository.get_by_id.assert_called_once_with(mock_gadget_read.id)
        mock_fetch_result.assert_called_once_with(ANY, "non-existent-uuid")
        mock_fetch_metadata.assert_called_once_with(ANY, "non-existent-uuid")


@pytest.mark.asyncio
async def test_gadget_zap_by_uuid_returns_task_result(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_gadget_read: GadgetRead,
    mock_gadget_zap_task: GadgetZapTask,
):
    """Test that gadget_zap_by_uuid returns task_result when it's available."""

    service = GadgetService(mock_gadget_repository, mock_allow_acls, mock_settings)
    mock_gadget_repository.get_by_id = AsyncMock(return_value=mock_gadget_read)

    with contextlib.ExitStack() as stack:
        mock_fetch_result = stack.enter_context(
            patch(
                "app.services.v1.gadgets.fetch_task_result",
                return_value=mock_gadget_zap_task.model_dump(),
            )
        )
        mock_fetch_metadata = stack.enter_context(
            patch("app.services.v1.gadgets.fetch_task_metadata")
        )
        result = await service.gadget_zap_by_uuid(mock_gadget_read.id, "test-uuid")

        mock_gadget_repository.get_by_id.assert_called_once_with(mock_gadget_read.id)
        mock_fetch_result.assert_called_once_with(ANY, "test-uuid")
        mock_fetch_metadata.assert_not_called()
        assert isinstance(result, GadgetZapTask)
        assert result.uuid == "test-uuid"
        assert result.id == mock_gadget_read.id
        assert result.state == "PENDING"
        assert result.duration == 5
        assert result.runtime == 0


@pytest.mark.asyncio
async def test_gadget_zap_by_uuid_not_found(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
):
    """Test NotFoundError when attempting to zap a non-existent gadget."""

    service = GadgetService(mock_gadget_repository, mock_allow_acls, mock_settings)
    mock_gadget_repository.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await service.gadget_zap_by_uuid(
            gadget_id=123,
            task_uuid="not-a-real-uuid",
        )

    # raising the exception is all that needs to be tested
