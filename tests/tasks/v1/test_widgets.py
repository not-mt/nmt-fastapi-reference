# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Tests for widget tasks."""

from app.models.v1.widgets import Widget
from app.schemas.v1.widgets import WidgetZapTask
from app.tasks.v1.widgets import widget_zap_task


def test_widget_zap_task(monkeypatch, mock_db_session, mock_task):
    """
    Test the widget_zap_task logic directly (bypassing Huey scheduler)
    """

    # mock the metadata fetching and storing functions locally
    def mock_fetch_task_metadata(huey_app, task_id):
        return WidgetZapTask(
            uuid="test-uuid",
            state="RUNNING",
            id=1,
            duration=1,
            runtime=1,
        )

    def mock_store_task_metadata(huey_app, task_id, task_md):
        pass

    monkeypatch.setattr(
        "app.tasks.v1.widgets.fetch_task_metadata",
        mock_fetch_task_metadata,
    )
    monkeypatch.setattr(
        "app.tasks.v1.widgets.store_task_metadata",
        mock_store_task_metadata,
    )
    # we do not want to actually sleep on time.sleep()
    monkeypatch.setattr("time.sleep", lambda *args, **kwargs: None)

    # NOTE: we are calling the task function directly, skipping the @huey_app.task
    #   decorator, and then we "unwrap" the @with_sync_session because that will
    #   clobber the db_session=mock_db_session that we are providing directly to the
    #   task

    widget_zap_task.func.__wrapped__(
        request_id="test-request-id",
        widget_id=1,
        duration=1,
        db_session=mock_db_session,
        task=mock_task,
    )

    # Assert DB interactions
    mock_db_session.get.assert_called_once_with(Widget, 1)
    mock_db_session.commit.assert_called_once()

    # Assert business logic applied to the object
    updated_widget = mock_db_session.get.return_value
    assert updated_widget.force == 11
