# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Tests for gadget tasks."""

from unittest.mock import MagicMock

import pytest

from app.schemas.v1.gadgets import GadgetZapTask
from app.tasks.v1.gadgets import gadget_zap_task


@pytest.fixture
def mock_gadget():
    """
    Fixture for a mock gadget dict (as stored in MongoDB).
    """
    return {
        "id": "id-1",
        "name": "ZapBot 5000",
        "force": 5,
    }


@pytest.fixture
def mock_mongo_db(mock_gadget):
    """
    Fixture for a mock MongoDB database with a 'gadgets' collection.
    """
    collection = MagicMock()
    collection.find_one.return_value = mock_gadget.copy()
    collection.update_one.return_value = None
    mongo_db = {"gadgets": collection}

    return mongo_db


def test_gadget_zap_task(monkeypatch, mock_mongo_db, mock_task, mock_gadget):
    """
    Test the gadget_zap_task logic directly (bypassing Huey scheduler).
    """

    # NOTE: patch time.sleep to avoid delay and metadata helpers
    monkeypatch.setattr("time.sleep", lambda *args, **kwargs: None)

    def mock_fetch_task_metadata(huey_app, task_id):
        return GadgetZapTask(
            uuid=task_id,
            state="PENDING",
            id=mock_gadget["id"],
            duration=1,
            runtime=0,
        )

    def mock_store_task_metadata(huey_app, task_id, task_md):
        pass  # NOTE: we could assert calls if needed

    monkeypatch.setattr(
        "app.tasks.v1.gadgets.fetch_task_metadata",
        mock_fetch_task_metadata,
    )
    monkeypatch.setattr(
        "app.tasks.v1.gadgets.store_task_metadata",
        mock_store_task_metadata,
    )

    # NOTE: we are calling the task function directly, skipping the @huey_app.task
    #   decorator, and then we "unwrap" the @with_sync_mongo_db wrapper because that will
    #   clobber the mongo_db=mock_mongo_db that we are providing directly to the
    #   task

    result = gadget_zap_task.func.__wrapped__(
        request_id="test-request-id",
        gadget_id=mock_gadget["id"],
        duration=1,
        task=mock_task,
        mongo_db=mock_mongo_db,
    )

    # validate the returned schema
    assert isinstance(result, GadgetZapTask)
    assert result.state == "SUCCESS"
    assert result.runtime == 1

    # verify DB interactions
    collection = mock_mongo_db["gadgets"]
    collection.find_one.assert_called_once_with({"id": mock_gadget["id"]})
    collection.update_one.assert_called_once_with(
        {"id": mock_gadget["id"]},
        {"$set": {"force": mock_gadget["force"] + 1}},
    )
