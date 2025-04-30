# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for core SQLAlchemy functions."""

from unittest.mock import MagicMock, patch

from app.core.v1.sqlalchemy import with_sync_session


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
