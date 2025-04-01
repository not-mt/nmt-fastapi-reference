# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for exception handlers."""

import json
from unittest.mock import MagicMock

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.errors.v1.exception_handlers import (
    index_out_of_range_error_handler,
    not_found_error_handler,
    server_error_handler,
)


def test_not_found_error_handler():
    """Test not_found_error_handler."""

    request = MagicMock(spec=Request)
    exc = HTTPException(status_code=404)
    response = not_found_error_handler(request, exc)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 404
    assert json.loads(response.body) == {"message": "Not Found"}


def test_server_error_handler():
    """Test server_error_handler."""

    request = MagicMock(spec=Request)
    exc = HTTPException(status_code=500)
    response = server_error_handler(request, exc)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 500
    assert json.loads(response.body) == {"message": "Internal Server Error"}


def test_index_out_of_range_error_handler():
    """Test index_out_of_range_error_handler."""

    request = MagicMock(spec=Request)
    exc = IndexError("Test index error")
    response = index_out_of_range_error_handler(request, exc)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 400
    assert json.loads(response.body) == {"message": "Index out of range"}
