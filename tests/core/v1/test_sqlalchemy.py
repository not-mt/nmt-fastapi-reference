# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for core SQLAlchemy functions."""

from unittest.mock import MagicMock, patch

from app.core.v1.settings import AppSettings, SqlAlchemySettings
from app.core.v1.sqlalchemy import with_sync_session


def test_with_ssl_mode_default_context():
    """
    Test creating an async_engine with ssl_mode="default"
    """
    test_url = "mysql+aiomysql://user:pass@host:3306"
    test_app_settings = AppSettings(
        sqlalchemy=SqlAlchemySettings(url=test_url, ssl_mode="default")
    )

    with patch(
        "app.core.v1.settings.get_app_settings",
        return_value=test_app_settings,
    ):
        # NOTE: reload module to re-execute initialization
        import importlib
        import ssl

        import app.core.v1.sqlalchemy as sqlalchemy_module

        importlib.reload(sqlalchemy_module)

        assert isinstance(sqlalchemy_module.ssl_context, ssl.SSLContext)


def test_with_sync_session_injects_db_session():
    """
    Test that with_sync_session injects a db_session and calls the wrapped function.
    """
    called_args = {}

    @with_sync_session
    def dummy_function(x, y, db_session=None):
        called_args["x"] = x
        called_args["y"] = y
        called_args["db_session"] = db_session
        return "success"

    with patch("app.core.v1.sqlalchemy.sync_session") as mock_sessionmaker:
        mock_context = mock_sessionmaker.return_value.__enter__.return_value
        mock_context.get.return_value = "mocked result"

        result = dummy_function(1, 2)

        # check return value and db_session injection
        assert result == "success"
        assert isinstance(called_args["db_session"], MagicMock)
        assert called_args["db_session"] is mock_context
