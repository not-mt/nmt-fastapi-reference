# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for router layer."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies.v1.database import get_db
from app.errors.v1.exceptions import NotFoundError
from app.repositories.v1.widgets import WidgetRepository
from app.routers.v1.widgets import authenticate_headers, get_widget_service
from app.schemas.v1.widgets import WidgetRead
from app.services.v1.widgets import WidgetService
from main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_create_widget_endpoint_success(
    mock_api_key: str,
    mock_widget_service: AsyncMock,
    mock_widget_read: WidgetRead,
):
    """Unit test for the create_widget endpoint."""

    # override the dependencies to use the mock service
    def override_get_widget_service():
        return mock_widget_service

    # override headers because authentication is outside of this unit test
    def override_authenticate_headers():
        return "Authenticated successfully."

    app.dependency_overrides[get_widget_service] = override_get_widget_service
    app.dependency_overrides[authenticate_headers] = override_authenticate_headers
    mock_widget_service.create_widget = AsyncMock(return_value=mock_widget_read)

    response = client.post(
        "/v1/widgets/",
        headers={"X-API-Key": mock_api_key},
        json={"name": "Test Widget"},
    )
    assert response.status_code == 200
    assert response.json() == mock_widget_read.model_dump()

    # Reset the dependency override
    app.dependency_overrides.pop(get_widget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)


@pytest.mark.asyncio
async def test_get_widget_service_dependency(mock_async_session: AsyncMock):
    """Test the get_widget_service dependency."""

    # Override the database dependency to use a mock session
    def override_get_db():
        return mock_async_session

    app.dependency_overrides[get_db] = override_get_db

    widget_service = get_widget_service(mock_async_session)

    assert isinstance(widget_service, WidgetService)
    assert isinstance(widget_service.widget_repository, WidgetRepository)
    assert widget_service.widget_repository.db == mock_async_session

    app.dependency_overrides.pop(get_db)


@pytest.mark.asyncio
async def test_get_widget_by_id_endpoint_success(
    mock_api_key: str,
    mock_widget_service: AsyncMock,
    mock_widget_read: WidgetRead,
):
    """Unit test for the get_widget_by_id endpoint when the widget exists."""

    # override the dependencies to use the mock service
    def override_get_widget_service():
        return mock_widget_service

    # override headers because authentication is outside of this unit test
    def override_authenticate_headers():
        return "Authenticated successfully."

    app.dependency_overrides[get_widget_service] = override_get_widget_service
    app.dependency_overrides[authenticate_headers] = override_authenticate_headers
    mock_widget_service.get_widget_by_id = AsyncMock(return_value=mock_widget_read)

    response = client.get(
        f"/v1/widgets/{mock_widget_read.id}",
        headers={"X-API-Key": mock_api_key},
    )

    assert response.status_code == 200
    assert response.json() == mock_widget_read.model_dump()

    app.dependency_overrides.pop(get_widget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)


@pytest.mark.asyncio
async def test_get_widget_by_id_endpoint_not_found(
    mock_api_key: str,
    mock_widget_service: AsyncMock,
):
    """Unit test for the get_widget_by_id endpoint when the widget does not exist."""

    # override the dependencies to use the mock service
    def override_get_widget_service():
        return mock_widget_service

    # override headers because authentication is outside of this unit test
    def override_authenticate_headers():
        return "Authenticated successfully."

    app.dependency_overrides[get_widget_service] = override_get_widget_service
    app.dependency_overrides[authenticate_headers] = override_authenticate_headers
    mock_widget_service.get_widget_by_id = AsyncMock(
        side_effect=NotFoundError(resource_id=123, resource_name="Widget"),
    )

    response = client.get(
        "/v1/widgets/123",
        headers={"X-API-Key": mock_api_key},
    )

    assert response.status_code == 404

    app.dependency_overrides.pop(get_widget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)
