# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""pytest fixtures for unit / integration tests."""

from unittest.mock import AsyncMock

import argon2
import pytest
from nmtfast.settings.v1.schemas import AuthApiKeySettings, SectionACL
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.v1.settings import AppSettings, AuthSettings, LoggingSettings
from app.repositories.v1.widgets import WidgetRepository
from app.schemas.v1.widgets import WidgetCreate, WidgetRead

ph = argon2.PasswordHasher()


@pytest.fixture
def mock_async_session() -> AsyncMock:
    """
    Fixture to provide a mock AsyncSession.
    """
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_api_key() -> str:
    """
    Fixture to return a predictable phrase that can be used to test hashing.
    """
    return "pytestapikey2"


@pytest.fixture(scope="function")
def mock_settings(mock_api_key: str) -> AppSettings:
    """
    Fixture to provide a generic AppSettings instance.
    """
    app_settings = AppSettings(
        auth=AuthSettings(
            swagger_token_url="http://localhost/token",
            id_providers={},
            clients={},
            api_keys={
                "key1": AuthApiKeySettings(
                    contact="some.user@domain.tld",
                    memo="pytest fixture",
                    hash=ph.hash(mock_api_key),
                    algo="argon2",
                    acls=[SectionACL(section_regex=".*", permissions=["*"])],
                )
            },
        ),
        logging=LoggingSettings(
            level="DEBUG",
            loggers=[
                {"name": "test_logger_1", "level": "DEBUG"},
                {"name": "test_logger_2", "level": "WARNING"},
            ],
        ),
    )
    return app_settings


@pytest.fixture
def mock_allow_acls() -> list[SectionACL]:
    """
    Fixture to provide a permissive set of ACLs.
    """
    acls = [
        SectionACL(section_regex=".*", permissions=["*"]),
    ]
    return acls


@pytest.fixture
def mock_deny_acls() -> list[SectionACL]:
    """
    Fixture to provide a restrictive set of ACLs.
    """
    acls = [
        SectionACL(section_regex=".*", permissions=[]),
    ]
    return acls


@pytest.fixture
def mock_widget_repository(mock_async_session: AsyncMock) -> WidgetRepository:
    """
    Fixture to provide a mock WidgetRepository.
    """
    return WidgetRepository(mock_async_session)


@pytest.fixture
def mock_widget_create() -> WidgetCreate:
    """
    Fixture to provide a test WidgetCreate instance.
    """
    return WidgetCreate(name="Test Widget")


@pytest.fixture
def mock_widget_read() -> WidgetRead:
    """
    Fixture to provide a test WidgetRead instance.
    """
    return WidgetRead(id=1, name="Test Widget", height="10", mass="5", force=20)
