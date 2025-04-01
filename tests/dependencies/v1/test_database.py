# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for database dependency injection functions."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.v1.database import get_db


@pytest.mark.asyncio
async def test_get_db_commits_on_success():
    """Test that get_db commits the session on success."""

    mock_session = AsyncMock(spec=AsyncSession)
    with patch("app.dependencies.v1.database.async_session") as mock_async_session:
        mock_async_session.return_value.__aenter__.return_value = mock_session
        async for session in get_db():
            pass  # Simulate successful operation
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()
        mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_db_rolls_back_on_exception():
    """Test that get_db rolls back the session on exception."""

    mock_session = AsyncMock(spec=AsyncSession)
    with patch("app.dependencies.v1.database.async_session") as mock_async_session:
        mock_async_session.return_value.__aenter__.return_value = mock_session
        gen = get_db()
        await gen.__anext__()
        with pytest.raises(ValueError):
            await gen.athrow(ValueError("Test Exception"))

        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()
        mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_db_closes_session():
    """Test that get_db closes the session."""

    mock_session = AsyncMock(spec=AsyncSession)
    with patch("app.dependencies.v1.database.async_session") as mock_async_session:
        mock_async_session.return_value.__aenter__.return_value = mock_session
        async for session in get_db():
            pass
        mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_db_yields_async_session():
    """Test that get_db yields an AsyncSession object."""

    mock_session = AsyncMock(spec=AsyncSession)
    with patch("app.dependencies.v1.database.async_session") as mock_async_session:
        mock_async_session.return_value.__aenter__.return_value = mock_session
        async for session in get_db():
            assert isinstance(session, AsyncSession)
            break
