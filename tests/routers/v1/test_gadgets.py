# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for router layer."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies.v1.sqlalchemy import get_sql_db
from app.errors.v1.exceptions import NotFoundError
from app.main import app
from app.repositories.v1.gadgets import GadgetRepository
from app.routers.v1.gadgets import authenticate_headers, get_gadget_service
from app.schemas.v1.gadgets import GadgetRead, GadgetZapTask
from app.services.v1.gadgets import GadgetService

client = TestClient(app)


@pytest.mark.asyncio
async def test_gadget_create_endpoint_success(
    mock_api_key: str,
    mock_gadget_service: AsyncMock,
    mock_gadget_read: GadgetRead,
):
    """Unit test for the gadget_create endpoint."""

    # override the dependencies to use the mock service
    def override_get_gadget_service():
        return mock_gadget_service

    # override headers because authentication is outside of this unit test
    def override_authenticate_headers():
        return "Authenticated successfully."

    app.dependency_overrides[get_gadget_service] = override_get_gadget_service
    app.dependency_overrides[authenticate_headers] = override_authenticate_headers
    mock_gadget_service.gadget_create = AsyncMock(return_value=mock_gadget_read)

    response = client.post(
        "/v1/gadgets/",
        headers={"X-API-Key": mock_api_key},
        json={"name": "Test Gadget"},
    )
    assert response.status_code == 200
    assert response.json() == mock_gadget_read.model_dump()

    # Reset the dependency override
    app.dependency_overrides.pop(get_gadget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)


@pytest.mark.asyncio
async def test_get_gadget_service_dependency(mock_async_session: AsyncMock):
    """Test the get_gadget_service dependency."""

    # Override the database dependency to use a mock session
    def override_get_sql_db():
        return mock_async_session

    app.dependency_overrides[get_sql_db] = override_get_sql_db

    gadget_service = get_gadget_service(mock_async_session)

    assert isinstance(gadget_service, GadgetService)
    assert isinstance(gadget_service.gadget_repository, GadgetRepository)
    assert gadget_service.gadget_repository.db == mock_async_session

    app.dependency_overrides.pop(get_sql_db)


@pytest.mark.asyncio
async def test_gadget_get_by_id_endpoint_success(
    mock_api_key: str,
    mock_gadget_service: AsyncMock,
    mock_gadget_read: GadgetRead,
):
    """Unit test for the gadget_get_by_id endpoint when the gadget exists."""

    # override the dependencies to use the mock service
    def override_get_gadget_service():
        return mock_gadget_service

    # override headers because authentication is outside of this unit test
    def override_authenticate_headers():
        return "Authenticated successfully."

    app.dependency_overrides[get_gadget_service] = override_get_gadget_service
    app.dependency_overrides[authenticate_headers] = override_authenticate_headers
    mock_gadget_service.gadget_get_by_id = AsyncMock(return_value=mock_gadget_read)

    response = client.get(
        f"/v1/gadgets/{mock_gadget_read.id}",
        headers={"X-API-Key": mock_api_key},
    )

    assert response.status_code == 200
    assert response.json() == mock_gadget_read.model_dump()

    app.dependency_overrides.pop(get_gadget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)


@pytest.mark.asyncio
async def test_gadget_get_by_id_endpoint_not_found(
    mock_api_key: str,
    mock_gadget_service: AsyncMock,
):
    """Unit test for the gadget_get_by_id endpoint when the gadget does not exist."""

    # override the dependencies to use the mock service
    def override_get_gadget_service():
        return mock_gadget_service

    # override headers because authentication is outside of this unit test
    def override_authenticate_headers():
        return "Authenticated successfully."

    app.dependency_overrides[get_gadget_service] = override_get_gadget_service
    app.dependency_overrides[authenticate_headers] = override_authenticate_headers
    mock_gadget_service.gadget_get_by_id = AsyncMock(
        side_effect=NotFoundError(resource_id=123, resource_name="Gadget"),
    )

    response = client.get(
        "/v1/gadgets/123",
        headers={"X-API-Key": mock_api_key},
    )
    assert response.status_code == 404

    app.dependency_overrides.pop(get_gadget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)


@pytest.mark.asyncio
async def test_gadget_zap_endpoint_success(
    mock_api_key: str,
    mock_gadget_service: AsyncMock,
    mock_gadget_read: GadgetRead,
    mock_gadget_zap_task: GadgetZapTask,
):
    """Unit test for the gadget_zap endpoint."""

    # override the dependencies to use the mock service
    def override_get_gadget_service():
        return mock_gadget_service

    # override headers because authentication is outside of this unit test
    def override_authenticate_headers():
        return "Authenticated successfully."

    app.dependency_overrides[get_gadget_service] = override_get_gadget_service
    app.dependency_overrides[authenticate_headers] = override_authenticate_headers
    mock_gadget_service.gadget_get_by_id = AsyncMock(return_value=mock_gadget_read)

    response = client.post(
        f"/v1/gadgets/{mock_gadget_read.id}/zap",
        headers={"X-API-Key": mock_api_key},
        json={"duration": 1},
    )
    assert response.status_code == 202
    assert response.json()["state"] == mock_gadget_zap_task.model_dump()["state"]

    # Reset the dependency override
    app.dependency_overrides.pop(get_gadget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)


@pytest.mark.asyncio
async def test_gadget_zap_endpoint_not_found(
    mock_api_key: str,
    mock_gadget_service: AsyncMock,
):
    """Unit test for the gadget_zap endpoint when gadget ID does not exist."""

    # override the dependencies to use the mock service
    def override_get_gadget_service():
        return mock_gadget_service

    # override headers because authentication is outside of this unit test
    def override_authenticate_headers():
        return "Authenticated successfully."

    app.dependency_overrides[get_gadget_service] = override_get_gadget_service
    app.dependency_overrides[authenticate_headers] = override_authenticate_headers
    mock_gadget_service.gadget_zap = AsyncMock(
        side_effect=NotFoundError(resource_id=123, resource_name="Gadget"),
    )

    response = client.post(
        "/v1/gadgets/123/zap",
        headers={"X-API-Key": mock_api_key},
        json={"duration": 1},
    )
    assert response.status_code == 404

    # Reset the dependency override
    app.dependency_overrides.pop(get_gadget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)


@pytest.mark.asyncio
async def test_gadget_zap_endpoint_status_success(
    mock_api_key: str,
    mock_gadget_service: AsyncMock,
    mock_gadget_read: GadgetRead,
    mock_gadget_zap_task: GadgetZapTask,
):
    """Unit test for the gadget_zap endpoint."""

    # override the dependencies to use the mock service
    def override_get_gadget_service():
        return mock_gadget_service

    # override headers because authentication is outside of this unit test
    def override_authenticate_headers():
        return "Authenticated successfully."

    app.dependency_overrides[get_gadget_service] = override_get_gadget_service
    app.dependency_overrides[authenticate_headers] = override_authenticate_headers
    mock_gadget_service.gadget_get_by_id = AsyncMock(return_value=mock_gadget_read)

    response = client.post(
        f"/v1/gadgets/{mock_gadget_read.id}/zap",
        headers={"X-API-Key": mock_api_key},
        json={"duration": 1},
    )
    assert response.status_code == 202
    assert response.json()["state"] == mock_gadget_zap_task.model_dump()["state"]

    uuid = response.json()["uuid"]
    response = client.get(
        f"/v1/gadgets/{mock_gadget_read.id}/zap/{uuid}/status",
        headers={"X-API-Key": mock_api_key},
    )
    assert response.status_code == 200
    assert response.json()["uuid"] == uuid

    # Reset the dependency override
    app.dependency_overrides.pop(get_gadget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)


@pytest.mark.asyncio
async def test_gadget_zap_endpoint_status_not_found(
    mock_api_key: str,
    mock_gadget_service: AsyncMock,
):
    """Unit test for the gadget_zap endpoint."""

    # override the dependencies to use the mock service
    def override_get_gadget_service():
        return mock_gadget_service

    # override headers because authentication is outside of this unit test
    def override_authenticate_headers():
        return "Authenticated successfully."

    app.dependency_overrides[get_gadget_service] = override_get_gadget_service
    app.dependency_overrides[authenticate_headers] = override_authenticate_headers
    mock_gadget_service.gadget_zap_by_uuid = AsyncMock(
        side_effect=NotFoundError(resource_id=123, resource_name="Gadget"),
    )

    response = client.get(
        "/v1/gadgets/123/zap/not-a-real-uuid/status",
        headers={"X-API-Key": mock_api_key},
    )
    assert response.status_code == 404

    # Reset the dependency override
    app.dependency_overrides.pop(get_gadget_service, None)
    app.dependency_overrides.pop(authenticate_headers, None)
