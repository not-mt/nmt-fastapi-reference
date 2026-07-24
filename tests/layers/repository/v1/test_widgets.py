# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for repository layer."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.v1.exceptions import ResourceNotFoundError
from app.layers.repository.v1.widgets import WidgetRepository
from app.schemas.dto.v1.widgets import WidgetCreate, WidgetUpdate
from app.schemas.orm.v1.widgets import Widget, WidgetZapTask


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
    return WidgetCreate(name="Test Widget", height="10cm", mass="5kg", force=20)


@pytest.fixture
def mock_db_widget():
    """
    Fixture to create a mock Widget database object.
    """
    return Widget(id=1, name="Test Widget", height="10cm", mass="5kg", force=20)


@pytest.mark.asyncio
async def test_widget_create(
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
    result = await repository.widget_create(mock_widget_create)

    mock_async_session.add.assert_called_once()
    mock_async_session.commit.assert_called_once()
    mock_async_session.refresh.assert_called_once()

    assert isinstance(result, Widget)
    assert result.name == mock_widget_create.name


@pytest.mark.asyncio
async def test_widget_get_by_id_found(
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
async def test_widget_get_by_id_not_found(mock_async_session: AsyncMock):
    """Test retrieving a widget by ID when it does not exist."""

    repository = WidgetRepository(mock_async_session)
    mock_async_session.get.return_value = None

    with pytest.raises(ResourceNotFoundError):
        await repository.get_by_id(123)


@pytest.mark.asyncio
async def test_update_force_success(
    mock_async_session: AsyncMock,
    mock_db_widget: Widget,
):
    """Test successfully updating the force value of a widget."""

    repository = WidgetRepository(mock_async_session)
    mock_async_session.get.return_value = mock_db_widget
    mock_async_session.commit.return_value = None
    mock_async_session.refresh.return_value = None

    new_force = 42
    result = await repository.update_force(mock_db_widget.id, new_force)

    assert result is mock_db_widget
    assert result.force == new_force


@pytest.mark.asyncio
async def test_update_force_widget_not_found(mock_async_session: AsyncMock):
    """Test update_force raises ResourceNotFoundError when widget does not exist."""

    repository = WidgetRepository(mock_async_session)
    mock_async_session.get.return_value = None

    with pytest.raises(ResourceNotFoundError, match="Widget with ID 1 not found"):
        await repository.update_force(1, 123)


@pytest.mark.asyncio
async def test_get_all(
    mock_async_session: AsyncMock,
    mock_db_widget: Widget,
):
    """
    Test retrieving all widgets with pagination.
    """
    repository = WidgetRepository(mock_async_session)

    # Mock count query
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    # Mock select query
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [mock_db_widget]
    select_result = MagicMock()
    select_result.scalars.return_value = scalars_mock

    mock_async_session.execute = AsyncMock(side_effect=[count_result, select_result])

    widgets, total = await repository.get_all(page=1, page_size=10)

    assert total == 1
    assert len(widgets) == 1
    assert widgets[0] is mock_db_widget


@pytest.mark.asyncio
async def test_get_all_with_search(
    mock_async_session: AsyncMock,
    mock_db_widget: Widget,
):
    """
    Test retrieving all widgets with a search filter.
    """
    repository = WidgetRepository(mock_async_session)

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [mock_db_widget]
    select_result = MagicMock()
    select_result.scalars.return_value = scalars_mock

    mock_async_session.execute = AsyncMock(side_effect=[count_result, select_result])

    widgets, total = await repository.get_all(search="Test")

    assert total == 1
    assert len(widgets) == 1


@pytest.mark.asyncio
async def test_update_success(
    mock_async_session: AsyncMock,
    mock_db_widget: Widget,
):
    """
    Test updating a widget when it exists.
    """
    repository = WidgetRepository(mock_async_session)
    mock_async_session.get.return_value = mock_db_widget
    mock_async_session.commit.return_value = None
    mock_async_session.refresh.return_value = None

    result = await repository.update(1, WidgetUpdate(name="Updated"))

    assert result is mock_db_widget
    assert result.name == "Updated"


@pytest.mark.asyncio
async def test_update_not_found(mock_async_session: AsyncMock):
    """
    Test updating a widget when it does not exist.
    """
    repository = WidgetRepository(mock_async_session)
    mock_async_session.get.return_value = None

    with pytest.raises(ResourceNotFoundError):
        await repository.update(999, WidgetUpdate(name="nope"))


@pytest.mark.asyncio
async def test_delete_success(
    mock_async_session: AsyncMock,
    mock_db_widget: Widget,
):
    """
    Test deleting a widget when it exists.
    """
    repository = WidgetRepository(mock_async_session)
    mock_async_session.get.return_value = mock_db_widget
    mock_async_session.delete.return_value = None
    mock_async_session.commit.return_value = None

    await repository.delete(1)

    mock_async_session.delete.assert_called_once_with(mock_db_widget)


@pytest.mark.asyncio
async def test_delete_not_found(mock_async_session: AsyncMock):
    """
    Test deleting a widget when it does not exist.
    """
    repository = WidgetRepository(mock_async_session)
    mock_async_session.get.return_value = None

    with pytest.raises(ResourceNotFoundError):
        await repository.delete(999)


@pytest.mark.asyncio
async def test_bulk_delete(mock_async_session: AsyncMock):
    """
    Test bulk deleting widgets.
    """
    repository = WidgetRepository(mock_async_session)
    mock_result = MagicMock()
    mock_result.rowcount = 2
    mock_async_session.execute = AsyncMock(return_value=mock_result)
    mock_async_session.commit.return_value = None

    count = await repository.bulk_delete([1, 2])

    assert count == 2


@pytest.mark.asyncio
async def test_bulk_update(mock_async_session: AsyncMock):
    """
    Test bulk updating widgets.
    """
    repository = WidgetRepository(mock_async_session)
    mock_result = MagicMock()
    mock_result.rowcount = 3
    mock_async_session.execute = AsyncMock(return_value=mock_result)
    mock_async_session.commit.return_value = None

    count = await repository.bulk_update([1, 2, 3], WidgetUpdate(name="bulk"))

    assert count == 3


@pytest.mark.asyncio
async def test_bulk_update_no_fields(mock_async_session: AsyncMock):
    """
    Test bulk update with no fields returns 0 without DB call.
    """
    repository = WidgetRepository(mock_async_session)
    count = await repository.bulk_update([1], WidgetUpdate())

    assert count == 0


@pytest.mark.asyncio
async def test_zap_task_create(mock_async_session: AsyncMock):
    """Test creating a zap task record in the repository."""
    from uuid import uuid4

    repository = WidgetRepository(mock_async_session)
    widget_id = 1
    task_uuid = uuid4()

    mock_async_session.add.return_value = None
    mock_async_session.flush.return_value = None
    mock_async_session.refresh.return_value = None

    mock_async_session.add.side_effect = lambda task: setattr(task, "id", 1)

    result = await repository.zap_task_create(
        widget_id=widget_id,
        task_uuid=str(task_uuid),
        duration=5,
    )

    mock_async_session.add.assert_called_once()
    mock_async_session.flush.assert_called_once()
    mock_async_session.refresh.assert_called_once()

    assert isinstance(result, WidgetZapTask)
    assert result.widget_id == widget_id
    assert result.task_uuid == str(task_uuid)
    assert result.state == "PENDING"


@pytest.mark.asyncio
async def test_zap_task_update(mock_async_session: AsyncMock):
    """Test updating a zap task record in the repository."""
    from uuid import uuid4

    repository = WidgetRepository(mock_async_session)
    task_uuid = uuid4()

    mock_task = WidgetZapTask(
        id=1,
        widget_id=1,
        task_uuid=str(task_uuid),
        state="PENDING",
    )

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_task
    mock_async_session.execute = AsyncMock(return_value=result_mock)
    mock_async_session.flush.return_value = None
    mock_async_session.refresh.return_value = None

    result = await repository.zap_task_update(
        task_uuid=str(task_uuid),
        state="RUNNING",
    )

    mock_async_session.execute.assert_called_once()
    mock_async_session.flush.assert_called_once()
    mock_async_session.refresh.assert_called_once()

    assert result is mock_task
    assert result.state == "RUNNING"


@pytest.mark.asyncio
async def test_zap_task_update_not_found(mock_async_session: AsyncMock):
    """Test zap_task_update raises ResourceNotFoundError when task does not exist."""
    from uuid import uuid4

    repository = WidgetRepository(mock_async_session)
    task_uuid = uuid4()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_async_session.execute = AsyncMock(return_value=result_mock)

    with pytest.raises(ResourceNotFoundError):
        await repository.zap_task_update(task_uuid=str(task_uuid), state="RUNNING")


@pytest.mark.asyncio
async def test_zap_task_list(mock_async_session: AsyncMock):
    """Test listing zap tasks for a widget with pagination."""
    from uuid import uuid4

    repository = WidgetRepository(mock_async_session)
    widget_id = 1
    task_uuid_1 = uuid4()
    task_uuid_2 = uuid4()

    task_1 = WidgetZapTask(
        id=1, widget_id=widget_id, task_uuid=str(task_uuid_1), state="SUCCESS"
    )
    task_2 = WidgetZapTask(
        id=2, widget_id=widget_id, task_uuid=str(task_uuid_2), state="PENDING"
    )

    # Mock count query
    mock_async_session.scalar = AsyncMock(return_value=2)

    # Mock select query
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [task_1, task_2]
    select_result = MagicMock()
    select_result.scalars.return_value = scalars_mock

    mock_async_session.execute = AsyncMock(return_value=select_result)

    tasks, total = await repository.zap_task_list(
        widget_id=widget_id, page=1, page_size=10
    )

    assert total == 2
    assert len(tasks) == 2
    assert tasks[0] is task_1


@pytest.mark.asyncio
async def test_zap_task_list_empty(mock_async_session: AsyncMock):
    """Test listing zap tasks when none exist for a widget."""
    repository = WidgetRepository(mock_async_session)
    widget_id = 999

    mock_async_session.scalar = AsyncMock(return_value=0)

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    select_result = MagicMock()
    select_result.scalars.return_value = scalars_mock

    mock_async_session.execute = AsyncMock(return_value=select_result)

    tasks, total = await repository.zap_task_list(
        widget_id=widget_id, page=1, page_size=10
    )

    assert total == 0
    assert len(tasks) == 0


@pytest.mark.asyncio
async def test_update_last_task_success(mock_async_session: AsyncMock):
    """Test updating the last_task_uuid and last_task_status on a widget."""
    from uuid import uuid4

    repository = WidgetRepository(mock_async_session)
    widget_id = 1
    task_uuid = uuid4()

    mock_widget = Widget(
        id=widget_id, name="Test Widget", height="10cm", mass="5kg", force=20
    )

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_widget
    mock_async_session.execute = AsyncMock(return_value=result_mock)
    mock_async_session.flush.return_value = None
    mock_async_session.refresh.return_value = None

    result = await repository.update_last_task(
        widget_id=widget_id,
        task_uuid=str(task_uuid),
        status="SUCCESS",
    )

    mock_async_session.execute.assert_called_once()
    mock_async_session.flush.assert_called_once()
    mock_async_session.refresh.assert_called_once()

    assert result is mock_widget
    assert result.last_task_uuid == str(task_uuid)
    assert result.last_task_status == "SUCCESS"


@pytest.mark.asyncio
async def test_update_last_task_widget_not_found(mock_async_session: AsyncMock):
    """Test update_last_task raises ResourceNotFoundError when widget does not exist."""
    from uuid import uuid4

    repository = WidgetRepository(mock_async_session)
    task_uuid = uuid4()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_async_session.execute = AsyncMock(return_value=result_mock)

    with pytest.raises(ResourceNotFoundError):
        await repository.update_last_task(
            widget_id=999,
            task_uuid=str(task_uuid),
            status="SUCCESS",
        )

    mock_async_session.execute.assert_called_once()
    mock_async_session.flush.assert_not_called()
    mock_async_session.refresh.assert_not_called()


@pytest.mark.asyncio
async def test_zap_task_list_with_search(mock_async_session: AsyncMock):
    """Test listing zap tasks with a search filter."""
    from uuid import uuid4

    repository = WidgetRepository(mock_async_session)
    widget_id = 1
    task_uuid_1 = uuid4()

    task_1 = WidgetZapTask(
        id=1, widget_id=widget_id, task_uuid=str(task_uuid_1), state="SUCCESS"
    )

    # Mock scalar for count
    mock_async_session.scalar = AsyncMock(return_value=1)

    # Mock select query
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [task_1]
    select_result = MagicMock()
    select_result.scalars.return_value = scalars_mock

    mock_async_session.execute = AsyncMock(return_value=select_result)

    tasks, total = await repository.zap_task_list(
        widget_id=widget_id, search="SUCCESS", page=1, page_size=10
    )

    assert total == 1
    assert len(tasks) == 1


@pytest.mark.asyncio
async def test_zap_task_list_total_none(mock_async_session: AsyncMock):
    """Test zap_task_list falls back to total=0 when scalar returns None."""
    repository = WidgetRepository(mock_async_session)
    widget_id = 999

    mock_async_session.scalar = AsyncMock(return_value=None)

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    select_result = MagicMock()
    select_result.scalars.return_value = scalars_mock

    mock_async_session.execute = AsyncMock(return_value=select_result)

    tasks, total = await repository.zap_task_list(
        widget_id=widget_id, page=1, page_size=10
    )

    assert total == 0
    assert len(tasks) == 0


@pytest.mark.asyncio
async def test_get_zap_task_by_uuid_found(mock_async_session: AsyncMock):
    """Test retrieving a zap task by UUID scoped to a widget."""
    from uuid import uuid4

    repository = WidgetRepository(mock_async_session)
    widget_id = 1
    task_uuid = str(uuid4())

    mock_task = WidgetZapTask(
        id=1,
        widget_id=widget_id,
        task_uuid=task_uuid,
        state="SUCCESS",
        duration=5,
        runtime=4,
    )

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_task
    mock_async_session.execute = AsyncMock(return_value=result_mock)

    result = await repository.get_zap_task_by_uuid(widget_id, task_uuid)

    mock_async_session.execute.assert_called_once()
    assert result is mock_task
    assert result.task_uuid == task_uuid
    assert result.state == "SUCCESS"


@pytest.mark.asyncio
async def test_get_zap_task_by_uuid_not_found(mock_async_session: AsyncMock):
    """Test get_zap_task_by_uuid returns None when task does not exist."""
    repository = WidgetRepository(mock_async_session)
    task_uuid = "non-existent-uuid"

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_async_session.execute = AsyncMock(return_value=result_mock)

    result = await repository.get_zap_task_by_uuid(999, task_uuid)

    assert result is None


@pytest.mark.asyncio
async def test_get_zap_task_by_uuid_scoped_to_widget(mock_async_session: AsyncMock):
    """Test that get_zap_task_by_uuid filters by both widget_id and task_uuid."""
    from uuid import uuid4

    repository = WidgetRepository(mock_async_session)
    widget_id = 1
    task_uuid = str(uuid4())

    mock_task = WidgetZapTask(
        id=1,
        widget_id=widget_id,
        task_uuid=task_uuid,
        state="PENDING",
    )

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_task
    mock_async_session.execute = AsyncMock(return_value=result_mock)

    await repository.get_zap_task_by_uuid(widget_id, task_uuid)

    call_args = mock_async_session.execute.call_args[0][0]
    assert str(widget_id) in str(call_args)


@pytest.mark.asyncio
async def test_zap_task_list_asc_order(mock_async_session: AsyncMock):
    """Test listing zap tasks with ascending sort order."""
    from uuid import uuid4

    repository = WidgetRepository(mock_async_session)
    widget_id = 1
    task_uuid_1 = uuid4()

    task_1 = WidgetZapTask(
        id=1, widget_id=widget_id, task_uuid=str(task_uuid_1), state="SUCCESS"
    )

    # Mock scalar for count
    mock_async_session.scalar = AsyncMock(return_value=1)

    # Mock select query
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [task_1]
    select_result = MagicMock()
    select_result.scalars.return_value = scalars_mock

    mock_async_session.execute = AsyncMock(return_value=select_result)

    tasks, total = await repository.zap_task_list(
        widget_id=widget_id, page=1, page_size=10, sort_order="asc"
    )

    assert total == 1
    assert len(tasks) == 1
