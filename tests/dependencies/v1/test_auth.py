# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for auth dependency injection functions."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from nmtfast.auth.v1.exceptions import AuthenticationError
from nmtfast.settings.v1.schemas import SectionACL

from app.dependencies.v1.auth import (
    authenticate_headers,
    get_acls,
    process_api_key_header,
    process_bearer_token,
)


@pytest.mark.asyncio
async def test_process_api_key_header_valid(mock_settings):
    """Test/mock a valid API key result for authenticate_api_key() call."""

    with patch(
        "app.dependencies.v1.auth.authenticate_api_key",
        new=AsyncMock(return_value="API key successfully authenticated."),
    ):
        result = await process_api_key_header("valid-api-key", mock_settings)
        assert result == "API key successfully authenticated."


@pytest.mark.asyncio
async def test_process_api_key_header_invalid(mock_settings):
    """Test/mock an invalid API key result for authenticate_api_key() call."""

    # invalid key
    with pytest.raises(HTTPException) as exc:
        await process_api_key_header("invalid-api-key", mock_settings)
    assert exc.value.status_code == 403

    # missing key
    with pytest.raises(HTTPException) as exc:
        await process_api_key_header("", mock_settings)
    assert exc.value.status_code == 403

    # simulate raising AuthenticationError
    with patch(
        "app.dependencies.v1.auth.authenticate_api_key",
        new=AsyncMock(side_effect=AuthenticationError("API key invalid")),
    ):
        with pytest.raises(HTTPException) as exc:
            await process_api_key_header("invalid-api-key", mock_settings)

    # simulate empty ACL list
    with patch(
        "app.dependencies.v1.auth.authenticate_api_key",
        new=AsyncMock(return_value=[]),  # empty list of ACLs
    ):
        with pytest.raises(HTTPException) as exc:
            await process_api_key_header("invalid-api-key", mock_settings)


@pytest.mark.asyncio
async def test_process_api_key_header_authentication_error(mock_settings):
    """Test process_api_key_header raises HTTPException on authentication failure."""

    with patch(
        "app.dependencies.v1.auth.authenticate_api_key",
        new=AsyncMock(side_effect=AuthenticationError("API key invalid")),
    ):
        with pytest.raises(HTTPException) as exc:
            await process_api_key_header("invalid-api-key", mock_settings)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_process_bearer_token_valid(mock_settings):
    """Test/mock a valid JWT result for authenticate_token() call."""

    with patch(
        "app.dependencies.v1.auth.authenticate_token",
        new=AsyncMock(
            return_value=[
                SectionACL(section_regex=".*", permissions=["*"]),
            ]
        ),
    ):
        result = await process_bearer_token(
            "Bearer part1.part2.part3",
            mock_settings,
        )
        assert result == "Token successfully authenticated."


@pytest.mark.asyncio
async def test_process_bearer_token_invalid(mock_settings):
    """Test/mock an invalid JWT result for authenticate_token() call."""

    # test authenticate_token returning an invalid token
    with patch(
        "app.dependencies.v1.auth.authenticate_token",
        new=AsyncMock(
            side_effect=HTTPException(403, "Invalid token"),
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            await process_bearer_token("Bearer invalid-token", mock_settings)
        assert exc.value.status_code == 403

        with pytest.raises(HTTPException) as exc:
            await process_bearer_token("no-bearer", mock_settings)
        assert exc.value.status_code == 401

    # test authenticate_token returning a blank list of ACLs
    with patch(
        "app.dependencies.v1.auth.authenticate_token",
        new=AsyncMock(return_value=[]),  # empty list of ACLs
    ):
        with pytest.raises(HTTPException) as exc:
            await process_bearer_token(
                "Bearer part1.part2.part3",
                mock_settings,
            )
        assert exc.value.status_code == 403

    # test raising AuthenticationError during authenticate_token
    with patch(
        "app.dependencies.v1.auth.authenticate_token",
        new=AsyncMock(
            side_effect=AuthenticationError("Token authentication failed"),
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            await process_bearer_token("Bearer some.valid.token", mock_settings)
        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_process_bearer_token_invalid_format(mock_settings):
    """Test process_bearer_token rejects tokens with invalid format."""

    with pytest.raises(HTTPException) as exc:
        await process_bearer_token("Bearer invalid-token-no-dots", mock_settings)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_authenticate_headers_with_api_key(mock_settings):
    """Test/mock a valid API key result for process_api_key_header() call."""

    # successful authn
    with patch(
        "app.dependencies.v1.auth.process_api_key_header",
        new=AsyncMock(
            return_value="API key successfully authenticated.",
        ),
    ):
        result = await authenticate_headers(
            api_key="valid-api-key",
            token=None,
            settings=mock_settings,
        )
        assert result == "API key successfully authenticated."

    # simulate raising AuthenticationError
    with patch(
        "app.dependencies.v1.auth.process_api_key_header",
        new=AsyncMock(
            side_effect=AuthenticationError("API key authentication failed"),
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            await authenticate_headers(
                api_key="invalid-api-key",
                token=None,
                settings=mock_settings,
            )
        assert exc.value.status_code == 403

    # simulate an empty list of ACLs
    with patch(
        "app.dependencies.v1.auth.process_api_key_header",
        new=AsyncMock(return_value=[]),  # empty list of ACLs
    ):
        with pytest.raises(HTTPException) as exc:
            await authenticate_headers(
                api_key="invalid-api-key",
                token=None,
                settings=mock_settings,
            )
        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_authenticate_headers_with_token(mock_settings):
    """Test/mock a valid JWT result for process_bearer_token() call."""

    # successful authn
    with patch(
        "app.dependencies.v1.auth.process_bearer_token",
        new=AsyncMock(
            return_value="Bearer token successfully authenticated.",
        ),
    ):
        result = await authenticate_headers(
            api_key=None,
            token="Bearer part1.part2.part3",
            settings=mock_settings,
        )
        assert result == "Bearer token successfully authenticated."

    # simulate raising AuthenticationError
    with patch(
        "app.dependencies.v1.auth.process_bearer_token",
        new=AsyncMock(
            side_effect=AuthenticationError("Token authentication failed"),
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            await authenticate_headers(
                api_key=None,
                token="Bearer some.valid.token",
                settings=mock_settings,
            )
        assert exc.value.status_code == 403

    # simulate an empty list of ACLs
    with patch(
        "app.dependencies.v1.auth.process_bearer_token",
        new=AsyncMock(return_value=[]),  # empty list of ACLs
    ):
        with pytest.raises(HTTPException) as exc:
            await authenticate_headers(
                api_key=None,
                token="not.valid.token",
                settings=mock_settings,
            )
        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_authenticate_headers_missing_both(mock_settings):
    """Test authenticate_headers raises HTTPException when missing headers."""

    with pytest.raises(HTTPException) as exc:
        await authenticate_headers(api_key=None, token=None, settings=mock_settings)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_authenticate_headers_with_both_raises_error(mock_settings):
    """Test/mock a invalid result with both an API key and JWT."""

    with pytest.raises(HTTPException) as exc:
        await authenticate_headers(
            api_key="valid-api-key",
            token="Bearer part1.part2.part3",
            settings=mock_settings,
        )

    # NOTE: exc is scoped for the entire function
    assert exc.value.status_code == 403
    assert "mutually exclusive" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_get_acls_with_api_key(mock_settings):
    """Test/mock valid ACLs from authenticate_api_key() call."""

    mock_request = AsyncMock()
    mock_request.headers = {"X-API-Key": "valid-api-key"}
    with patch(
        "app.dependencies.v1.auth.authenticate_api_key",
        new=AsyncMock(
            return_value=[
                SectionACL(section_regex=".*", permissions=["*"]),
            ]
        ),
    ):
        result = await get_acls(mock_request, mock_settings)
        assert result[0].permissions == ["*"]


@pytest.mark.asyncio
async def test_get_acls_with_token(mock_settings):
    """Test/mock valid ACLs from authenticate_token() call."""

    mock_request = AsyncMock()
    mock_request.headers = {
        "Authorization": "Bearer part1.part2.part3",
    }
    with patch(
        "app.dependencies.v1.auth.authenticate_token",
        new=AsyncMock(
            return_value=[
                SectionACL(section_regex=".*", permissions=["*"]),
            ]
        ),
    ):
        result = await get_acls(mock_request, mock_settings)
        assert result[0].permissions == ["*"]


@pytest.mark.asyncio
async def test_get_acls_unauthorized(mock_settings):
    """Test/mock unauthorized ACLs from get_acl() call."""

    mock_request = AsyncMock()
    mock_request.headers = {}  # empty headers will be rejected
    with pytest.raises(HTTPException) as exc:
        await get_acls(mock_request, mock_settings)

    # NOTE: exc is scoped for the entire function
    assert exc.value.status_code == 403
    assert "Unauthorized" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_get_acls_no_auth_headers(mock_settings):
    """Test get_acls raises HTTPException when no API key or token is provided."""

    request = AsyncMock()
    request.headers = {}

    with pytest.raises(HTTPException) as exc:
        await get_acls(request, mock_settings)
    assert exc.value.status_code == 403
    assert "Unauthorized" in exc.value.detail


@pytest.mark.asyncio
async def test_get_acls_invalid_api_key(mock_settings):
    """Test get_acls raises HTTPException when API key authentication fails."""

    request = AsyncMock()
    request.headers = {"X-API-Key": "invalid-api-key"}

    with patch(
        "app.dependencies.v1.auth.authenticate_api_key",
        new=AsyncMock(side_effect=AuthenticationError("Invalid API key")),
    ):
        with pytest.raises(HTTPException) as exc:
            await get_acls(request, mock_settings)
        assert exc.value.status_code == 403
        assert "Invalid API key" in exc.value.detail


@pytest.mark.asyncio
async def test_get_acls_invalid_token(mock_settings):
    """Test get_acls raises HTTPException when token authentication fails."""

    request = AsyncMock()
    request.headers = {"Authorization": "Bearer mangled-token"}

    with patch(
        "app.dependencies.v1.auth.authenticate_token",
        new=AsyncMock(side_effect=AuthenticationError("Invalid token")),
    ):
        with pytest.raises(HTTPException) as exc:
            await get_acls(request, mock_settings)
        assert exc.value.status_code == 403
        assert "Invalid token" in exc.value.detail

    request = AsyncMock()
    request.headers = {"Authorization": "Bearer some.invalid.token"}

    with patch(
        "app.dependencies.v1.auth.authenticate_token",
        new=AsyncMock(side_effect=AuthenticationError("Invalid token")),
    ):
        with pytest.raises(HTTPException) as exc:
            await get_acls(request, mock_settings)
        assert exc.value.status_code == 403
        assert "Invalid token" in exc.value.detail
