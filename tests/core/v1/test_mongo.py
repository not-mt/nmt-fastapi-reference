# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for core MongoDB functions."""

from unittest.mock import MagicMock, patch

from app.core.v1.settings import AppSettings, MongoSettings


def test_mongo_clients_initialization_with_url():
    """
    Test clients are initialized when mongo.url is present.
    """
    test_app_settings = AppSettings(
        mongo=MongoSettings(url="mongodb://localhost:27017", db="test-db")
    )
    mock_async_client = MagicMock()
    mock_sync_client = MagicMock()
    mock_sync_client.address = ("localhost", 27017)

    with (
        patch(
            "app.core.v1.settings.get_app_settings",
            return_value=test_app_settings,
        ),
        patch(
            "pymongo.AsyncMongoClient",
            return_value=mock_async_client,
        ),
        patch(
            "pymongo.MongoClient",
            return_value=mock_sync_client,
        ),
    ):
        # NOTE: reload module to re-execute initialization code
        import importlib

        import app.core.v1.mongo as mongo_module

        importlib.reload(mongo_module)

        assert mongo_module.async_client is mock_async_client
        assert mongo_module.sync_client is mock_sync_client
        assert mongo_module.sync_client is not None
        assert mongo_module.sync_client.address == ("localhost", 27017)


def test_mongo_clients_not_initialized_without_url():
    """Test clients remain None when mongo.url is empty string."""

    test_app_settings = AppSettings(mongo=MongoSettings(url="", db="test-db"))

    with patch(
        "app.core.v1.settings.get_app_settings",
        return_value=test_app_settings,
    ):
        # NOTE: reload module to re-execute initialization code
        import importlib

        import app.core.v1.mongo as mongo_module

        importlib.reload(mongo_module)

        # verify clients were NOT initialized
        assert mongo_module.async_client is None
        assert mongo_module.sync_client is None


def test_with_sync_mongo_db_decorator():
    """
    Test the with_sync_mongo_db decorator.
    """
    test_app_settings = AppSettings(
        mongo=MongoSettings(url="mongodb://localhost:27017", db="test-db")
    )
    mock_db = MagicMock()
    mock_db.name = "test-db"
    mock_sync_client = MagicMock()
    mock_sync_client.__getitem__.return_value = mock_db

    with (
        patch(
            "app.core.v1.settings.get_app_settings",
            return_value=test_app_settings,
        ),
        patch(
            "pymongo.MongoClient",
            return_value=mock_sync_client,
        ),
    ):
        # NOTE: reload module to get fresh state
        import importlib

        import app.core.v1.mongo as mongo_module

        importlib.reload(mongo_module)

        called = False

        @mongo_module.with_sync_mongo_db()
        def test_function(mongo_db=None):
            nonlocal called
            called = True
            assert mongo_db is not None
            assert mongo_db.name == "test-db"

        test_function()
        assert called
