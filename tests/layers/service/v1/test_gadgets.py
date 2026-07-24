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

from app.core.v1.settings import AppSettings
from app.errors.v1.exceptions import ResourceNotFoundError
from app.layers.repository.v1.gadgets import GadgetRepository
from app.layers.service.v1.gadgets import GadgetService
from app.schemas.dto.v1.gadgets import (
    GadgetCreate,
    GadgetRead,
    GadgetUpdate,
    GadgetZap,
    GadgetZapTask,
    GadgetZapTaskRead,
    GadgetZapTaskRecord,
)


@pytest.fixture
def mock_cache():
    """
    Fixture to produce a mock AppCacheBase.
    """
    return AsyncMock(spec=AppCacheBase)


@pytest.fixture
def mock_gadget_repository(mock_mongo_db: AsyncMock) -> GadgetRepository:
    """
    Fixture to provide a mock GadgetRepository.
    """
    return GadgetRepository(mock_mongo_db)


@pytest.fixture
def mock_gadget_create() -> GadgetCreate:
    """
    Fixture to provide a test GadgetCreate instance.
    """
    return GadgetCreate(name="Test Gadget", height="10cm", mass="5kg", force=20)


@pytest.fixture
def mock_gadget_read() -> GadgetRead:
    """
    Fixture to provide a test GadgetRead instance.
    """
    return GadgetRead(id="id-1", name="Test Gadget", height="10", mass="5", force=20)


@pytest.fixture
def mock_gadget_zap() -> GadgetZap:
    """
    Fixture for a sample GadgetZap payload.
    """
    return GadgetZap(duration=5)


@pytest.fixture
def mock_gadget_zap_task() -> GadgetZapTask:
    """
    Fixture for a sample GadgetZapTask.
    """
    return GadgetZapTask(
        uuid="test-uuid", gadget_id="id-1", state="PENDING", duration=5, runtime=0
    )


@pytest.mark.asyncio
async def test_gadget_create(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_gadget_create: GadgetCreate,
    mock_gadget_read: GadgetRead,
):
    """Test successful creation of a gadget."""

    service = GadgetService(
        mock_gadget_repository, mock_allow_acls, mock_settings, mock_cache
    )
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
    mock_cache: AppCacheBase,
    mock_gadget_create: GadgetCreate,
):
    """
    Test authorization error during gadget creation.
    """
    service = GadgetService(
        mock_gadget_repository, mock_deny_acls, mock_settings, mock_cache
    )

    with pytest.raises(AuthorizationError):
        await service.gadget_create(mock_gadget_create)

    # raising the exception is all that needs to be tested


@pytest.mark.asyncio
async def test_gadget_get_by_id_success(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_gadget_read: GadgetRead,
):
    """
    Test successful retrieval of a gadget by ID.
    """
    service = GadgetService(
        mock_gadget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_gadget_repository.get_by_id = AsyncMock(return_value=mock_gadget_read)
    result = await service.gadget_get_by_id(mock_gadget_read.id)

    mock_gadget_repository.get_by_id.assert_called_once()
    assert isinstance(result, GadgetRead)
    assert result.id == mock_gadget_read.id


@pytest.mark.asyncio
async def test_gadget_get_by_id_authorization_error(
    mock_gadget_repository: AsyncMock,
    mock_deny_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
):
    """
    Test authorization error during gadget retrieval.
    """
    service = GadgetService(
        mock_gadget_repository, mock_deny_acls, mock_settings, mock_cache
    )

    with pytest.raises(AuthorizationError):
        await service.gadget_get_by_id("123")

    # raising the exception is all that needs to be tested


@pytest.mark.asyncio
async def test_gadget_zap_success(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_gadget_read: GadgetRead,
    mock_gadget_zap: GadgetZap,
):
    """
    Test successful zapping of a gadget.
    """
    service = GadgetService(
        mock_gadget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_gadget_repository.get_by_id = AsyncMock(return_value=mock_gadget_read)
    mock_gadget_repository.collection.insert_one = AsyncMock()
    mock_update_result = MagicMock()
    mock_update_result.matched_count = 1
    mock_gadget_repository.collection.update_one = AsyncMock(
        return_value=mock_update_result
    )

    mock_schedule_result = MagicMock()
    mock_schedule_result.id = "test-uuid"
    mock_gadget_zap_task = MagicMock()
    mock_gadget_zap_task.schedule = MagicMock(return_value=mock_schedule_result)

    with contextlib.ExitStack() as stack:
        mock_zap_task = stack.enter_context(
            patch(
                "app.layers.service.v1.gadgets.gadget_zap_task",
                mock_gadget_zap_task,
            )
        )
        mock_store_metadata = stack.enter_context(
            patch("app.layers.service.v1.gadgets.store_task_metadata")
        )
        result = await service.gadget_zap(mock_gadget_read.id, mock_gadget_zap)

        mock_gadget_repository.get_by_id.assert_called_once_with(mock_gadget_read.id)
        mock_zap_task.schedule.assert_called_once()
        mock_store_metadata.assert_called_once_with(
            ANY,  # huey_app
            "test-uuid",
            {
                "uuid": "test-uuid",
                "gadget_id": mock_gadget_read.id,
                "state": "PENDING",
                "duration": mock_gadget_zap.duration,
                "runtime": 0,
                "result": None,
            },
        )
        assert isinstance(result, GadgetZapTask)
        assert result.uuid == "test-uuid"
        assert result.gadget_id == mock_gadget_read.id
        assert result.duration == mock_gadget_zap.duration


@pytest.mark.asyncio
async def test_gadget_zap_success_no_match(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_gadget_read: GadgetRead,
    mock_gadget_zap: GadgetZap,
):
    """
    Test gadget_zap raises ResourceNotFoundError when update_one matches 0 docs.
    """
    service = GadgetService(
        mock_gadget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_gadget_repository.get_by_id = AsyncMock(return_value=mock_gadget_read)
    mock_gadget_repository.zap_task_create = AsyncMock()
    mock_update_result = MagicMock()
    mock_update_result.matched_count = 0
    mock_gadget_repository.collection.update_one = AsyncMock(
        return_value=mock_update_result
    )

    mock_schedule_result = MagicMock()
    mock_schedule_result.id = "test-uuid"
    mock_gadget_zap_task = MagicMock()
    mock_gadget_zap_task.schedule = MagicMock(return_value=mock_schedule_result)

    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.layers.service.v1.gadgets.gadget_zap_task",
                mock_gadget_zap_task,
            )
        )
        with pytest.raises(ResourceNotFoundError, match="Gadget"):
            await service.gadget_zap(mock_gadget_read.id, mock_gadget_zap)


@pytest.mark.asyncio
async def test_gadget_zap_by_uuid_not_found_task(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_gadget_read: GadgetRead,
):
    """
    Test ResourceNotFoundError when the zap task metadata is not found.
    """

    service = GadgetService(
        mock_gadget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_gadget_repository.get_by_id = AsyncMock(return_value=mock_gadget_read)
    mock_gadget_repository.get_zap_task_by_uuid = AsyncMock(return_value=None)

    with contextlib.ExitStack() as stack:
        mock_fetch_result = stack.enter_context(
            patch("app.layers.service.v1.gadgets.fetch_task_result", return_value=None)
        )
        mock_fetch_metadata = stack.enter_context(
            patch(
                "app.layers.service.v1.gadgets.fetch_task_metadata", return_value=None
            )
        )

        with pytest.raises(ResourceNotFoundError, match="Task"):
            await service.gadget_zap_by_uuid(mock_gadget_read.id, "non-existent-uuid")

        mock_gadget_repository.get_by_id.assert_called_once_with(mock_gadget_read.id)
        mock_fetch_result.assert_called_once_with(ANY, "non-existent-uuid")
        mock_fetch_metadata.assert_called_once_with(ANY, "non-existent-uuid")


@pytest.mark.asyncio
async def test_gadget_zap_by_uuid_returns_task_result(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_gadget_read: GadgetRead,
    mock_gadget_zap_task: GadgetZapTask,
):
    """
    Test that gadget_zap_by_uuid returns task_result when it's available.
    """

    service = GadgetService(
        mock_gadget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_gadget_repository.get_by_id = AsyncMock(return_value=mock_gadget_read)
    mock_gadget_repository.get_zap_task_by_uuid = AsyncMock(return_value=None)

    with contextlib.ExitStack() as stack:
        mock_fetch_result = stack.enter_context(
            patch(
                "app.layers.service.v1.gadgets.fetch_task_result",
                return_value=mock_gadget_zap_task.model_dump(),
            )
        )
        mock_fetch_metadata = stack.enter_context(
            patch("app.layers.service.v1.gadgets.fetch_task_metadata")
        )
        result = await service.gadget_zap_by_uuid(mock_gadget_read.id, "test-uuid")

        mock_gadget_repository.get_by_id.assert_called_once_with(mock_gadget_read.id)
        mock_fetch_result.assert_called_once_with(ANY, "test-uuid")
        mock_fetch_metadata.assert_not_called()
        assert isinstance(result, GadgetZapTask)
        assert result.uuid == "test-uuid"
        assert result.gadget_id == mock_gadget_read.id
        assert result.state == "PENDING"
        assert result.duration == 5
        assert result.runtime == 0


@pytest.mark.asyncio
async def test_gadget_zap_by_uuid_not_found(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_gadget_read: GadgetRead,
):
    """
    Test ResourceNotFoundError when attempting to zap a non-existent gadget.
    """
    service = GadgetService(
        mock_gadget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_gadget_repository.get_by_id = AsyncMock(return_value=mock_gadget_read)
    mock_gadget_repository.get_zap_task_by_uuid = AsyncMock(return_value=None)

    with pytest.raises(ResourceNotFoundError):
        await service.gadget_zap_by_uuid(
            gadget_id="123",
            task_uuid="not-a-real-uuid",
        )

    # raising the exception is all that needs to be tested


@pytest.mark.asyncio
async def test_gadget_list(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_gadget_read: GadgetRead,
):
    """
    Test successful listing of gadgets.
    """
    service = GadgetService(
        mock_gadget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_gadget_repository.get_all = AsyncMock(return_value=([mock_gadget_read], 1))
    result, total = await service.gadget_list()

    assert total == 1
    assert len(result) == 1
    assert isinstance(result[0], GadgetRead)


@pytest.mark.asyncio
async def test_gadget_update(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_gadget_read: GadgetRead,
):
    """
    Test successful update of a gadget.
    """
    service = GadgetService(
        mock_gadget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_gadget_repository.update = AsyncMock(return_value=mock_gadget_read)
    result = await service.gadget_update("id-1", GadgetUpdate(name="Updated"))

    assert isinstance(result, GadgetRead)
    mock_gadget_repository.update.assert_called_once()


@pytest.mark.asyncio
async def test_gadget_delete(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
):
    """
    Test successful deletion of a gadget.
    """
    service = GadgetService(
        mock_gadget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_gadget_repository.delete = AsyncMock(return_value=None)
    await service.gadget_delete("id-1")

    mock_gadget_repository.delete.assert_called_once_with("id-1")


@pytest.mark.asyncio
async def test_gadget_bulk_delete(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
):
    """
    Test successful bulk deletion of gadgets.
    """
    service = GadgetService(
        mock_gadget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_gadget_repository.bulk_delete = AsyncMock(return_value=2)
    result = await service.gadget_bulk_delete(["g1", "g2"])

    assert result == 2


@pytest.mark.asyncio
async def test_gadget_bulk_update(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
):
    """
    Test successful bulk update of gadgets.
    """
    service = GadgetService(
        mock_gadget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_gadget_repository.bulk_update = AsyncMock(return_value=3)
    result = await service.gadget_bulk_update(
        ["g1", "g2", "g3"], GadgetUpdate(name="bulk")
    )

    assert result == 3


@pytest.mark.asyncio
async def test_gadget_zap_persists_task_state(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_gadget_read: GadgetRead,
    mock_gadget_zap: GadgetZap,
):
    """Test that gadget_zap persists task state via repository calls."""
    service = GadgetService(
        mock_gadget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_gadget_repository.get_by_id = AsyncMock(return_value=mock_gadget_read)
    mock_gadget_repository.collection.update_one = AsyncMock()
    mock_gadget_repository.zap_task_create = AsyncMock()

    mock_schedule_result = MagicMock()
    mock_schedule_result.id = "persist-test-uuid"
    mock_gadget_zap_task = MagicMock()
    mock_gadget_zap_task.schedule = MagicMock(return_value=mock_schedule_result)

    with contextlib.ExitStack() as stack:
        stack.enter_context(patch("app.layers.service.v1.gadgets.store_task_metadata"))
        stack.enter_context(
            patch(
                "app.layers.service.v1.gadgets.gadget_zap_task",
                mock_gadget_zap_task,
            )
        )
        await service.gadget_zap(mock_gadget_read.id, mock_gadget_zap)

        mock_gadget_repository.zap_task_create.assert_called_once()
        create_call = mock_gadget_repository.zap_task_create.call_args
        assert create_call[1]["gadget_id"] == mock_gadget_read.id
        assert create_call[1]["task_uuid"] == "persist-test-uuid"
        assert create_call[1]["duration"] == mock_gadget_zap.duration


@pytest.mark.asyncio
async def test_gadget_zap_by_uuid_persists_error(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_gadget_read: GadgetRead,
):
    """Test that gadget_zap_by_uuid updates task to FAILED on RuntimeError."""
    service = GadgetService(
        mock_gadget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_gadget_repository.get_by_id = AsyncMock(return_value=mock_gadget_read)
    mock_gadget_repository.get_zap_task_by_uuid = AsyncMock(return_value=None)

    with contextlib.ExitStack() as stack:
        stack.enter_context(patch("app.layers.service.v1.gadgets.store_task_metadata"))
        mock_gadget_repository.zap_task_update = AsyncMock()

        stack.enter_context(
            patch(
                "app.layers.service.v1.gadgets.fetch_task_result",
                side_effect=RuntimeError("gadget error"),
            )
        )
        stack.enter_context(
            patch(
                "app.layers.service.v1.gadgets.fetch_task_metadata",
                return_value={
                    "uuid": "error-test-uuid",
                    "gadget_id": mock_gadget_read.id,
                    "state": "PENDING",
                    "duration": 5,
                    "runtime": 0,
                },
            )
        )

        with pytest.raises(RuntimeError, match="gadget error"):
            await service.gadget_zap_by_uuid(mock_gadget_read.id, "error-test-uuid")

        mock_gadget_repository.zap_task_update.assert_called()
        update_call = mock_gadget_repository.zap_task_update.call_args
        assert update_call[1]["state"] == "FAILED"


@pytest.mark.asyncio
async def test_gadget_zap_by_uuid_db_success(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_gadget_read: GadgetRead,
):
    """Test that gadget_zap_by_uuid returns DB SUCCESS record without querying Huey."""
    service = GadgetService(
        mock_gadget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_gadget_repository.get_by_id = AsyncMock(return_value=mock_gadget_read)

    with contextlib.ExitStack() as stack:
        mock_gadget_repository.get_zap_task_by_uuid = AsyncMock(
            return_value={
                "task_uuid": "db-success-uuid",
                "state": "SUCCESS",
                "gadget_id": mock_gadget_read.id,
                "duration": 5,
                "runtime": 4,
                "result": {"gadget_id": mock_gadget_read.id, "new_force": 21},
            }
        )
        mock_fetch_result = stack.enter_context(
            patch("app.layers.service.v1.gadgets.fetch_task_result")
        )
        mock_fetch_metadata = stack.enter_context(
            patch("app.layers.service.v1.gadgets.fetch_task_metadata")
        )

        result = await service.gadget_zap_by_uuid(
            mock_gadget_read.id, "db-success-uuid"
        )

        mock_fetch_result.assert_not_called()
        mock_fetch_metadata.assert_not_called()
        assert isinstance(result, GadgetZapTask)
        assert result.uuid == "db-success-uuid"
        assert result.state == "SUCCESS"
        assert result.runtime == 4
        assert result.result == {"gadget_id": mock_gadget_read.id, "new_force": 21}


@pytest.mark.asyncio
async def test_gadget_zap_by_uuid_db_failed(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_gadget_read: GadgetRead,
):
    """Test that gadget_zap_by_uuid returns DB FAILED record without querying Huey."""
    service = GadgetService(
        mock_gadget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_gadget_repository.get_by_id = AsyncMock(return_value=mock_gadget_read)

    with contextlib.ExitStack() as stack:
        mock_gadget_repository.get_zap_task_by_uuid = AsyncMock(
            return_value={
                "task_uuid": "db-failed-uuid",
                "state": "FAILED",
                "gadget_id": mock_gadget_read.id,
                "duration": 5,
                "runtime": 3,
                "result": {"error": "some error"},
            }
        )
        mock_fetch_result = stack.enter_context(
            patch("app.layers.service.v1.gadgets.fetch_task_result")
        )
        mock_fetch_metadata = stack.enter_context(
            patch("app.layers.service.v1.gadgets.fetch_task_metadata")
        )

        result = await service.gadget_zap_by_uuid(mock_gadget_read.id, "db-failed-uuid")

        mock_fetch_result.assert_not_called()
        mock_fetch_metadata.assert_not_called()
        assert isinstance(result, GadgetZapTask)
        assert result.uuid == "db-failed-uuid"
        assert result.state == "FAILED"
        assert result.runtime == 3
        assert result.result == {"error": "some error"}


@pytest.mark.asyncio
async def test_gadget_zap_by_uuid_db_pending_falls_through(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_gadget_read: GadgetRead,
    mock_gadget_zap_task: GadgetZapTask,
):
    """Test that DB PENDING/RUNNING record falls through to Huey."""
    service = GadgetService(
        mock_gadget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_gadget_repository.get_by_id = AsyncMock(return_value=mock_gadget_read)

    with contextlib.ExitStack() as stack:
        mock_gadget_repository.get_zap_task_by_uuid = AsyncMock(
            return_value={
                "task_uuid": "in-progress-uuid",
                "state": "RUNNING",
                "gadget_id": mock_gadget_read.id,
                "duration": 5,
                "runtime": 2,
            }
        )
        stack.enter_context(
            patch(
                "app.layers.service.v1.gadgets.fetch_task_result",
                return_value=mock_gadget_zap_task.model_dump(),
            )
        )
        mock_fetch_metadata = stack.enter_context(
            patch("app.layers.service.v1.gadgets.fetch_task_metadata")
        )

        result = await service.gadget_zap_by_uuid(
            mock_gadget_read.id, "in-progress-uuid"
        )

        assert isinstance(result, GadgetZapTask)
        mock_fetch_metadata.assert_not_called()


@pytest.mark.asyncio
async def test_gadget_zap_by_uuid_db_none_no_huey_metadata(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_gadget_read: GadgetRead,
):
    """Test DB None + no Huey metadata raises ResourceNotFoundError."""
    service = GadgetService(
        mock_gadget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_gadget_repository.get_by_id = AsyncMock(return_value=mock_gadget_read)

    with contextlib.ExitStack() as stack:
        mock_gadget_repository.get_zap_task_by_uuid = AsyncMock(return_value=None)
        stack.enter_context(
            patch("app.layers.service.v1.gadgets.fetch_task_result", return_value=None)
        )
        stack.enter_context(
            patch(
                "app.layers.service.v1.gadgets.fetch_task_metadata", return_value=None
            )
        )

        with pytest.raises(ResourceNotFoundError, match="Task"):
            await service.gadget_zap_by_uuid(mock_gadget_read.id, "non-existent-uuid")


@pytest.mark.asyncio
async def test_gadget_zap_history(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_gadget_read: GadgetRead,
):
    """Test that gadget_zap_history calls the repository correctly."""
    service = GadgetService(
        mock_gadget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_gadget_repository.get_by_id = AsyncMock(return_value=mock_gadget_read)

    mock_gadget_repository.zap_task_list = AsyncMock(
        return_value=(
            [
                GadgetZapTaskRecord(
                    task_uuid="test-uuid",
                    state="SUCCESS",
                    gadget_id=mock_gadget_read.id,
                    duration=5,
                    runtime=4,
                    _id="task-1",
                )
            ],
            1,
        )
    )

    result, total = await service.gadget_zap_history(
        gadget_id=mock_gadget_read.id,
        page=1,
        page_size=10,
        sort_by="created_at",
        sort_order="desc",
        search=None,
    )

    mock_gadget_repository.get_by_id.assert_called_once_with(mock_gadget_read.id)
    mock_gadget_repository.zap_task_list.assert_called_once_with(
        gadget_id=mock_gadget_read.id,
        page=1,
        page_size=10,
        sort_by="created_at",
        sort_order="desc",
        search=None,
    )
    assert total == 1
    assert len(result) == 1
    assert isinstance(result[0], GadgetZapTaskRead)
    assert result[0].task_uuid == "test-uuid"


@pytest.mark.asyncio
async def test_gadget_zap_by_uuid_error_path_zap_task_update_raises(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_gadget_read: GadgetRead,
):
    """Test that gadget_zap_by_uuid catches ResourceNotFoundError from zap_task_update and re-raises original error."""
    service = GadgetService(
        mock_gadget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_gadget_repository.get_by_id = AsyncMock(return_value=mock_gadget_read)
    mock_gadget_repository.get_zap_task_by_uuid = AsyncMock(return_value=None)

    task_uuid = "error-test-uuid"

    with contextlib.ExitStack() as stack:
        stack.enter_context(patch("app.layers.service.v1.gadgets.store_task_metadata"))
        mock_gadget_repository.zap_task_update = AsyncMock(
            side_effect=ResourceNotFoundError(task_uuid, "GadgetZapTaskRecord")
        )

        stack.enter_context(
            patch(
                "app.layers.service.v1.gadgets.fetch_task_result",
                side_effect=RuntimeError("gadget error"),
            )
        )
        stack.enter_context(
            patch(
                "app.layers.service.v1.gadgets.fetch_task_metadata",
                return_value={
                    "uuid": task_uuid,
                    "gadget_id": mock_gadget_read.id,
                    "state": "PENDING",
                    "duration": 5,
                    "runtime": 0,
                },
            )
        )

        with pytest.raises(RuntimeError, match="gadget error"):
            await service.gadget_zap_by_uuid(mock_gadget_read.id, task_uuid)

        mock_gadget_repository.zap_task_update.assert_called_once()


@pytest.mark.asyncio
async def test_gadget_zap_by_uuid_fallback_metadata(
    mock_gadget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_gadget_read: GadgetRead,
):
    """Test that gadget_zap_by_uuid falls back to fetch_task_metadata when DB has no record and fetch_task_result returns None."""
    service = GadgetService(
        mock_gadget_repository, mock_allow_acls, mock_settings, mock_cache
    )
    mock_gadget_repository.get_by_id = AsyncMock(return_value=mock_gadget_read)
    mock_gadget_repository.get_zap_task_by_uuid = AsyncMock(return_value=None)

    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch("app.layers.service.v1.gadgets.fetch_task_result", return_value=None)
        )
        stack.enter_context(
            patch(
                "app.layers.service.v1.gadgets.fetch_task_metadata",
                return_value={
                    "uuid": "meta-uuid",
                    "gadget_id": mock_gadget_read.id,
                    "state": "PENDING",
                    "duration": 5,
                    "runtime": 0,
                },
            )
        )

        result = await service.gadget_zap_by_uuid(mock_gadget_read.id, "meta-uuid")

        assert isinstance(result, GadgetZapTask)
        assert result.uuid == "meta-uuid"
        assert result.state == "PENDING"
        assert result.gadget_id == mock_gadget_read.id
        assert result.duration == 5
        assert result.runtime == 0
