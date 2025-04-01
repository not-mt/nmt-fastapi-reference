# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""
Exception handlers for widget API operations.

This module provides custom exception handlers for FastAPI applications.
It ensures consistent error responses for widget-related exceptions
and common server-side errors.
"""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


def not_found_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle generic 404 HTTP exceptions.

    Args:
        request: The incoming HTTP request.
        exc: The raised HTTPException with status 404.

    Returns:
        JSONResponse: A 404 response with a generic error message.
    """
    return JSONResponse(
        status_code=404,
        content={"message": "Not Found"},
    )


def server_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle generic 500 HTTP exceptions.

    Args:
        request: The incoming HTTP request.
        exc: The raised HTTPException with status 500.

    Returns:
        JSONResponse: A 500 response with a generic error message.
    """
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error"},
    )


def index_out_of_range_error_handler(request: Request, exc: IndexError) -> JSONResponse:
    """
    Handle IndexError exceptions.

    Args:
        request: The incoming HTTP request.
        exc: The raised IndexError exception.

    Returns:
        JSONResponse: A 400 response indicating an invalid index access.
    """
    return JSONResponse(
        status_code=400,
        content={"message": "Index out of range"},
    )
