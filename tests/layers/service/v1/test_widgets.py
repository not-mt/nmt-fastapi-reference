# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for service/domain layer."""

import contextlib
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from aiokafka import AIOKafkaProducer
from nmtfast.auth.v1.exceptions import AuthorizationError
from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.settings.v1.schemas import SectionACL
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.v1.settings import AppSettings
from app.errors.v1.exceptions import ResourceNotFoundError
from app.layers.repository.v1.widgets import WidgetRepository
from app.layers.service.v1.widgets import WidgetService
from app.schemas.dto.v1.widgets import (
    WidgetCreate,
    WidgetRead,
    WidgetUpdate,
    WidgetZap,
    WidgetZapTask,
    WidgetZapTaskRead,
)
from app.schemas.orm.v1.widgets import Widget


@pytest.fixture
def mock_cache():
    """
    Fixture to return a mock AppCacheBase.
    """
    return AsyncMock(spec=AppCacheBase)


@pytest.fixture
def mock_kafka():
    """
    Fixture to generate a mock Kafka producer.
    """
    return AsyncMock(spec=AIOKafkaProducer)


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
    return WidgetCreate(name="Test Widget", height="10cm", mass="5kg", force=20)


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
    return WidgetZapTask(
        uuid="test-uuid", widget_id=1, state="PENDING", duration=5, runtime=0
    )


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
    mock_kafka: AIOKafkaProducer,
):
    """
    Test successful creation of a widget.
    """
    service = WidgetService(
        mock_widget_repository,
        mock_allow_acls,
        mock_settings,
        mock_cache,
        mock_kafka,
    )
    mock_widget_repository.widget_create = AsyncMock(return_value=mock_widget_read)
    result = await service.widget_create(mock_widget_create)

    mock_widget_repository.widget_create.assert_called_once()
    assert isinstance(result, WidgetRead)
    assert result.id == mock_widget_read.id

    mock_kafka.send.assert_called_once_with(
        topic="nmtfast-widgets",
        key="create-widget",
        value=WidgetRead.model_validate(mock_widget_read),
    )


@pytest.mark.asyncio
async def test_widget_get_by_id_success(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_widget_read: WidgetRead,
    mock_kafka: AIOKafkaProducer,
):
    """
    Test successful retrieval of a widget by ID.
    """
    service = WidgetService(
        mock_widget_repository,
        mock_allow_acls,
        mock_settings,
        mock_cache,
        mock_kafka,
    )
    mock_widget_repository.get_by_id = AsyncMock(return_value=mock_widget_read)
    result = await service.widget_get_by_id(1)

    mock_widget_repository.get_by_id.assert_called_once()
    assert isinstance(result, WidgetRead)
    assert result.id == mock_widget_read.id


@pytest.mark.asyncio
async def test_widget_get_by_id_authorization_error(
    mock_widget_repository: AsyncMock,
    mock_deny_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_kafka: AIOKafkaProducer,
):
    """
    Test authorization error during widget retrieval.
    """
    service = WidgetService(
        mock_widget_repository,
        mock_deny_acls,
        mock_settings,
        mock_cache,
        mock_kafka,
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
    mock_kafka: AIOKafkaProducer,
):
    """
    Test successful zapping of a widget.
    """
    service = WidgetService(
        mock_widget_repository,
        mock_allow_acls,
        mock_settings,
        mock_cache,
        mock_kafka,
    )
    mock_widget_repository.get_by_id = AsyncMock(return_value=mock_widget_read)
    mock_widget_repository.update_last_task = AsyncMock()
    mock_widget_repository.zap_task_create = AsyncMock()

    mock_async_result = MagicMock()
    mock_async_result.task.id = "test-uuid"

    with contextlib.ExitStack() as stack:
        mock_widget_zap_task_obj = MagicMock()
        mock_widget_zap_task_obj.schedule = MagicMock(
            return_value=MagicMock(id="test-uuid")
        )
        mock_zap_task = stack.enter_context(
            patch(
                "app.layers.service.v1.widgets.widget_zap_task",
                mock_widget_zap_task_obj,
            )
        )
        mock_store_metadata = stack.enter_context(
            patch("app.layers.service.v1.widgets.store_task_metadata")
        )
        result = await service.widget_zap(mock_widget_read.id, mock_widget_zap)

        mock_widget_repository.get_by_id.assert_called_once_with(mock_widget_read.id)
        mock_zap_task.schedule.assert_called_once()
        mock_store_metadata.assert_called_once_with(
            ANY,  # huey_app
            "test-uuid",
            {
                "uuid": "test-uuid",
                "state": "PENDING",
                "widget_id": mock_widget_read.id,
                "duration": mock_widget_zap.duration,
                "runtime": 0,
                "result": None,
            },
        )
        assert isinstance(result, WidgetZapTask)
        assert result.uuid == "test-uuid"
        assert result.widget_id == mock_widget_read.id
        assert result.duration == mock_widget_zap.duration


@pytest.mark.asyncio
async def test_widget_zap_by_uuid_not_found_task(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_widget_read: WidgetRead,
    mock_kafka: AIOKafkaProducer,
):
    """
    Test ResourceNotFoundError when the zap task metadata is not found.
    """
    service = WidgetService(
        mock_widget_repository,
        mock_allow_acls,
        mock_settings,
        mock_cache,
        mock_kafka,
    )
    mock_widget_repository.get_by_id = AsyncMock(return_value=mock_widget_read)
    mock_widget_repository.get_zap_task_by_uuid = AsyncMock(return_value=None)

    with contextlib.ExitStack() as stack:
        mock_fetch_result = stack.enter_context(
            patch("app.layers.service.v1.widgets.fetch_task_result", return_value=None)
        )
        mock_fetch_metadata = stack.enter_context(
            patch(
                "app.layers.service.v1.widgets.fetch_task_metadata", return_value=None
            )
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
    mock_kafka: AIOKafkaProducer,
):
    """
    Test that widget_zap_by_uuid returns task_result when it's available.
    """
    service = WidgetService(
        mock_widget_repository,
        mock_allow_acls,
        mock_settings,
        mock_cache,
        mock_kafka,
    )
    mock_widget_repository.get_by_id = AsyncMock(return_value=mock_widget_read)
    mock_widget_repository.get_zap_task_by_uuid = AsyncMock(return_value=None)

    with contextlib.ExitStack() as stack:
        mock_fetch_result = stack.enter_context(
            patch(
                "app.layers.service.v1.widgets.fetch_task_result",
                return_value=mock_widget_zap_task.model_dump(),
            )
        )
        mock_fetch_metadata = stack.enter_context(
            patch("app.layers.service.v1.widgets.fetch_task_metadata")
        )
        result = await service.widget_zap_by_uuid(mock_widget_read.id, "test-uuid")

        mock_widget_repository.get_by_id.assert_called_once_with(mock_widget_read.id)
        mock_fetch_result.assert_called_once_with(ANY, "test-uuid")
        mock_fetch_metadata.assert_not_called()
        assert isinstance(result, WidgetZapTask)
        assert result.uuid == "test-uuid"
        assert result.widget_id == mock_widget_read.id
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
    mock_kafka: AIOKafkaProducer,
):
    """
    Test ResourceNotFoundError when attempting to zap a non-existent widget.
    """
    service = WidgetService(
        mock_widget_repository,
        mock_allow_acls,
        mock_settings,
        mock_cache,
        mock_kafka,
    )
    mock_widget_repository.get_by_id = AsyncMock(return_value=mock_db_widget)
    mock_widget_repository.get_zap_task_by_uuid = AsyncMock(return_value=None)

    with pytest.raises(ResourceNotFoundError):
        await service.widget_zap_by_uuid(
            widget_id=123,
            task_uuid="not-a-real-uuid",
        )

    # raising the exception is all that needs to be tested


@pytest.mark.asyncio
async def test_widget_list(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_widget_read: WidgetRead,
    mock_kafka: AIOKafkaProducer,
):
    """
    Test successful listing of widgets.
    """
    service = WidgetService(
        mock_widget_repository,
        mock_allow_acls,
        mock_settings,
        mock_cache,
        mock_kafka,
    )
    mock_widget_repository.get_all = AsyncMock(return_value=([mock_widget_read], 1))
    result, total = await service.widget_list()

    assert total == 1
    assert len(result) == 1
    assert isinstance(result[0], WidgetRead)


@pytest.mark.asyncio
async def test_widget_update(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_widget_read: WidgetRead,
    mock_kafka: AIOKafkaProducer,
):
    """
    Test successful update of a widget.
    """
    service = WidgetService(
        mock_widget_repository,
        mock_allow_acls,
        mock_settings,
        mock_cache,
        mock_kafka,
    )
    mock_widget_repository.update = AsyncMock(return_value=mock_widget_read)
    result = await service.widget_update(1, WidgetUpdate(name="Updated"))

    assert isinstance(result, WidgetRead)
    mock_widget_repository.update.assert_called_once()


@pytest.mark.asyncio
async def test_widget_delete(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_kafka: AIOKafkaProducer,
):
    """
    Test successful deletion of a widget.
    """
    service = WidgetService(
        mock_widget_repository,
        mock_allow_acls,
        mock_settings,
        mock_cache,
        mock_kafka,
    )
    mock_widget_repository.delete = AsyncMock(return_value=None)
    await service.widget_delete(1)

    mock_widget_repository.delete.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_widget_bulk_delete(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_kafka: AIOKafkaProducer,
):
    """
    Test successful bulk deletion of widgets.
    """
    service = WidgetService(
        mock_widget_repository,
        mock_allow_acls,
        mock_settings,
        mock_cache,
        mock_kafka,
    )
    mock_widget_repository.bulk_delete = AsyncMock(return_value=2)
    result = await service.widget_bulk_delete([1, 2])

    assert result == 2


@pytest.mark.asyncio
async def test_widget_bulk_update(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_kafka: AIOKafkaProducer,
):
    """
    Test successful bulk update of widgets.
    """
    service = WidgetService(
        mock_widget_repository,
        mock_allow_acls,
        mock_settings,
        mock_cache,
        mock_kafka,
    )
    mock_widget_repository.bulk_update = AsyncMock(return_value=3)
    result = await service.widget_bulk_update([1, 2, 3], WidgetUpdate(name="bulk"))

    assert result == 3


@pytest.mark.asyncio
async def test_widget_zap_persists_task_state(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_widget_read: WidgetRead,
    mock_widget_zap: WidgetZap,
    mock_kafka: AIOKafkaProducer,
):
    """Test that widget_zap persists task state via repository calls."""
    service = WidgetService(
        mock_widget_repository,
        mock_allow_acls,
        mock_settings,
        mock_cache,
        mock_kafka,
    )
    mock_widget_repository.get_by_id = AsyncMock(return_value=mock_widget_read)
    mock_widget_repository.update_last_task = AsyncMock()
    mock_widget_repository.zap_task_create = AsyncMock()

    mock_schedule_result = MagicMock()
    mock_schedule_result.id = "persist-test-uuid"
    mock_widget_zap_task_func = MagicMock()
    mock_widget_zap_task_func.schedule = MagicMock(return_value=mock_schedule_result)

    with contextlib.ExitStack() as stack:
        stack.enter_context(patch("app.layers.service.v1.widgets.store_task_metadata"))
        stack.enter_context(
            patch(
                "app.layers.service.v1.widgets.widget_zap_task",
                mock_widget_zap_task_func,
            )
        )
        await service.widget_zap(mock_widget_read.id, mock_widget_zap)

        mock_widget_repository.zap_task_create.assert_called_once()
        create_call = mock_widget_repository.zap_task_create.call_args
        assert create_call[1]["widget_id"] == mock_widget_read.id
        assert create_call[1]["task_uuid"] == "persist-test-uuid"
        assert create_call[1]["duration"] == mock_widget_zap.duration


@pytest.mark.asyncio
async def test_widget_zap_by_uuid_db_success(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_widget_read: WidgetRead,
    mock_kafka: AIOKafkaProducer,
):
    """Test that widget_zap_by_uuid returns DB SUCCESS record without querying Huey."""
    service = WidgetService(
        mock_widget_repository,
        mock_allow_acls,
        mock_settings,
        mock_cache,
        mock_kafka,
    )
    mock_widget_repository.get_by_id = AsyncMock(return_value=mock_widget_read)

    from datetime import datetime

    from app.schemas.orm.v1.widgets import WidgetZapTask as WidgetZapTaskORM

    db_task = WidgetZapTaskORM(
        task_uuid="db-success-uuid",
        state="SUCCESS",
        widget_id=mock_widget_read.id,
        duration=5,
        runtime=4,
        result={"widget_id": mock_widget_read.id, "new_force": 21},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    with contextlib.ExitStack() as stack:
        mock_widget_repository.get_zap_task_by_uuid = AsyncMock(return_value=db_task)
        mock_fetch_result = stack.enter_context(
            patch("app.layers.service.v1.widgets.fetch_task_result")
        )
        mock_fetch_metadata = stack.enter_context(
            patch("app.layers.service.v1.widgets.fetch_task_metadata")
        )

        result = await service.widget_zap_by_uuid(
            mock_widget_read.id, "db-success-uuid"
        )

        mock_fetch_result.assert_not_called()
        mock_fetch_metadata.assert_not_called()
        assert isinstance(result, WidgetZapTask)
        assert result.uuid == "db-success-uuid"
        assert result.state == "SUCCESS"
        assert result.runtime == 4
        assert result.result == {"widget_id": mock_widget_read.id, "new_force": 21}


@pytest.mark.asyncio
async def test_widget_zap_by_uuid_db_failed(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_widget_read: WidgetRead,
    mock_kafka: AIOKafkaProducer,
):
    """Test that widget_zap_by_uuid returns DB FAILED record without querying Huey."""
    service = WidgetService(
        mock_widget_repository,
        mock_allow_acls,
        mock_settings,
        mock_cache,
        mock_kafka,
    )
    mock_widget_repository.get_by_id = AsyncMock(return_value=mock_widget_read)

    from datetime import datetime

    from app.schemas.orm.v1.widgets import WidgetZapTask as WidgetZapTaskORM

    db_task = WidgetZapTaskORM(
        task_uuid="db-failed-uuid",
        state="FAILED",
        widget_id=mock_widget_read.id,
        duration=5,
        runtime=3,
        result={"error": "some error"},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    with contextlib.ExitStack() as stack:
        mock_widget_repository.get_zap_task_by_uuid = AsyncMock(return_value=db_task)
        mock_fetch_result = stack.enter_context(
            patch("app.layers.service.v1.widgets.fetch_task_result")
        )
        mock_fetch_metadata = stack.enter_context(
            patch("app.layers.service.v1.widgets.fetch_task_metadata")
        )

        result = await service.widget_zap_by_uuid(mock_widget_read.id, "db-failed-uuid")

        mock_fetch_result.assert_not_called()
        mock_fetch_metadata.assert_not_called()
        assert isinstance(result, WidgetZapTask)
        assert result.uuid == "db-failed-uuid"
        assert result.state == "FAILED"
        assert result.runtime == 3
        assert result.result == {"error": "some error"}


@pytest.mark.asyncio
async def test_widget_zap_by_uuid_db_pending_falls_through(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_widget_read: WidgetRead,
    mock_widget_zap_task: WidgetZapTask,
    mock_kafka: AIOKafkaProducer,
):
    """Test that DB PENDING/RUNNING record falls through to Huey."""
    service = WidgetService(
        mock_widget_repository,
        mock_allow_acls,
        mock_settings,
        mock_cache,
        mock_kafka,
    )
    mock_widget_repository.get_by_id = AsyncMock(return_value=mock_widget_read)

    from datetime import datetime

    from app.schemas.orm.v1.widgets import WidgetZapTask as WidgetZapTaskORM

    db_task = WidgetZapTaskORM(
        task_uuid="in-progress-uuid",
        state="RUNNING",
        widget_id=mock_widget_read.id,
        duration=5,
        runtime=2,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    with contextlib.ExitStack() as stack:
        mock_widget_repository.get_zap_task_by_uuid = AsyncMock(return_value=db_task)
        stack.enter_context(
            patch(
                "app.layers.service.v1.widgets.fetch_task_result",
                return_value=mock_widget_zap_task.model_dump(),
            )
        )
        mock_fetch_metadata = stack.enter_context(
            patch("app.layers.service.v1.widgets.fetch_task_metadata")
        )

        result = await service.widget_zap_by_uuid(
            mock_widget_read.id, "in-progress-uuid"
        )

        assert isinstance(result, WidgetZapTask)
        mock_fetch_metadata.assert_not_called()


@pytest.mark.asyncio
async def test_widget_zap_by_uuid_db_none_no_huey_metadata(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_widget_read: WidgetRead,
    mock_kafka: AIOKafkaProducer,
):
    """Test DB None + no Huey metadata raises ResourceNotFoundError."""
    service = WidgetService(
        mock_widget_repository,
        mock_allow_acls,
        mock_settings,
        mock_cache,
        mock_kafka,
    )
    mock_widget_repository.get_by_id = AsyncMock(return_value=mock_widget_read)

    with contextlib.ExitStack() as stack:
        mock_widget_repository.get_zap_task_by_uuid = AsyncMock(return_value=None)
        stack.enter_context(
            patch("app.layers.service.v1.widgets.fetch_task_result", return_value=None)
        )
        stack.enter_context(
            patch(
                "app.layers.service.v1.widgets.fetch_task_metadata", return_value=None
            )
        )

        with pytest.raises(ResourceNotFoundError, match="Task"):
            await service.widget_zap_by_uuid(mock_widget_read.id, "non-existent-uuid")


@pytest.mark.asyncio
async def test_widget_zap_by_uuid_persists_error(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_widget_read: WidgetRead,
    mock_kafka: AIOKafkaProducer,
):
    """Test that widget_zap_by_uuid updates task to FAILED on RuntimeError."""
    service = WidgetService(
        mock_widget_repository,
        mock_allow_acls,
        mock_settings,
        mock_cache,
        mock_kafka,
    )
    mock_widget_repository.get_by_id = AsyncMock(return_value=mock_widget_read)
    mock_widget_repository.get_zap_task_by_uuid = AsyncMock(return_value=None)

    with contextlib.ExitStack() as stack:
        stack.enter_context(patch("app.layers.service.v1.widgets.store_task_metadata"))
        mock_widget_repository.zap_task_update = AsyncMock()

        stack.enter_context(
            patch(
                "app.layers.service.v1.widgets.fetch_task_result",
                side_effect=RuntimeError("task error"),
            )
        )
        stack.enter_context(
            patch(
                "app.layers.service.v1.widgets.fetch_task_metadata",
                return_value={
                    "uuid": "error-test-uuid",
                    "widget_id": mock_widget_read.id,
                    "state": "PENDING",
                    "duration": 5,
                    "runtime": 0,
                },
            )
        )

        with pytest.raises(RuntimeError, match="task error"):
            await service.widget_zap_by_uuid(mock_widget_read.id, "error-test-uuid")

        mock_widget_repository.zap_task_update.assert_called()
        update_call = mock_widget_repository.zap_task_update.call_args
        assert update_call[1]["state"] == "FAILED"


@pytest.mark.asyncio
async def test_widget_zap_by_uuid_error_path_zap_task_update_raises(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_widget_read: WidgetRead,
    mock_kafka: AIOKafkaProducer,
):
    """Test that widget_zap_by_uuid catches ResourceNotFoundError from zap_task_update and re-raises original error."""
    service = WidgetService(
        mock_widget_repository,
        mock_allow_acls,
        mock_settings,
        mock_cache,
        mock_kafka,
    )
    mock_widget_repository.get_by_id = AsyncMock(return_value=mock_widget_read)
    mock_widget_repository.get_zap_task_by_uuid = AsyncMock(return_value=None)

    task_uuid = "error-test-uuid"

    with contextlib.ExitStack() as stack:
        stack.enter_context(patch("app.layers.service.v1.widgets.store_task_metadata"))
        mock_widget_repository.zap_task_update = AsyncMock(
            side_effect=ResourceNotFoundError(task_uuid, "WidgetZapTask")
        )

        stack.enter_context(
            patch(
                "app.layers.service.v1.widgets.fetch_task_result",
                side_effect=RuntimeError("task error"),
            )
        )
        stack.enter_context(
            patch(
                "app.layers.service.v1.widgets.fetch_task_metadata",
                return_value={
                    "uuid": task_uuid,
                    "widget_id": mock_widget_read.id,
                    "state": "PENDING",
                    "duration": 5,
                    "runtime": 0,
                },
            )
        )

        with pytest.raises(RuntimeError, match="task error"):
            await service.widget_zap_by_uuid(mock_widget_read.id, task_uuid)

        mock_widget_repository.zap_task_update.assert_called_once()


@pytest.mark.asyncio
async def test_widget_zap_history(
    mock_widget_repository: AsyncMock,
    mock_allow_acls: list[SectionACL],
    mock_settings: AppSettings,
    mock_cache: AppCacheBase,
    mock_widget_read: WidgetRead,
    mock_widget_zap_task: WidgetZapTask,
    mock_kafka: AIOKafkaProducer,
):
    """Test that widget_zap_history calls the repository correctly."""
    service = WidgetService(
        mock_widget_repository,
        mock_allow_acls,
        mock_settings,
        mock_cache,
        mock_kafka,
    )
    mock_widget_repository.get_by_id = AsyncMock(return_value=mock_widget_read)

    from datetime import datetime

    from app.schemas.orm.v1.widgets import WidgetZapTask as WidgetZapTaskORM

    orm_task = WidgetZapTaskORM(
        task_uuid="test-uuid",
        state="SUCCESS",
        id=1,
        widget_id=mock_widget_read.id,
        duration=5,
        runtime=4,
        result=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    mock_widget_repository.zap_task_list = AsyncMock(return_value=([orm_task], 1))

    result, total = await service.widget_zap_history(
        widget_id=mock_widget_read.id, page=1, page_size=10
    )

    mock_widget_repository.get_by_id.assert_called_once_with(mock_widget_read.id)
    mock_widget_repository.zap_task_list.assert_called_once_with(
        widget_id=mock_widget_read.id,
        page=1,
        page_size=10,
        sort_by="created_at",
        sort_order="desc",
        search=None,
    )
    assert total == 1
    assert len(result) == 1
    assert isinstance(result[0], WidgetZapTaskRead)
    assert result[0].task_uuid == "test-uuid"
