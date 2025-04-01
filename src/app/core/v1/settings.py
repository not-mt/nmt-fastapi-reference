# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Application settings and defaults, defined with pydantic-settings."""

import logging

from nmtfast.settings.v1.config_files import get_config_files, load_config
from nmtfast.settings.v1.schemas import AuthSettings, LoggingSettings
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class SqlAlchemySettings(BaseModel):
    """SQLAlchemy database settings model."""

    url: str = "sqlite+aiosqlite:///./development.sqlite"


class AppSettings(BaseSettings):
    """Application settings model."""

    version: int = 1
    app_name: str = "My FastAPI App"
    database: SqlAlchemySettings = SqlAlchemySettings()
    auth: AuthSettings = AuthSettings(
        swagger_token_url="https://some.domain.tld/token",
        id_providers={
            # "provider_name": IDProvider(
            #     issuer_regex="^https://some.domain.tld$",
            #     jwks_endpoint="https://some.domain.tld/jwks.json",
            #     introspection_enabled=True,
            #     introspection_endpoint="https://some.domain.tld/introspection",
            #     keyid_enabled=False,
            #     keyid_endpoint="https://some.domain.tld/keyid",
            # )
        },
        clients={
            # "some_api_client": AuthClientSettings(
            #     provider="provider_name",
            #     claims={
            #         "client_id": "not_a_real_client",
            #     },
            #     acls=[
            #         SectionACL(
            #             section_regex="^not_a_real_section$",
            #             permissions=["read"],
            #             # NOTE: filters will be added later
            #             # filters=[
            #             #     FilterACL(
            #             #         scope="payload",
            #             #         action="allow",
            #             #         field="not_a_real_name",
            #             #         match_regex="^not_a_real_pattern$",
            #             #     )
            #             # ],
            #         )
            #     ],
            # )
        },
        api_keys={
            # "some_api_key":  AuthApiKeySettings(
            #     contact="user.domain@domain.tld",
            #     memo="some api key details here",
            #     hash="some_password_hash_goes_here",
            #     acls=[
            #         SectionACL(
            #             section_regex="^not_a_real_section$",
            #             permissions=["read"],
            #             # NOTE: filters will be added later
            #             # filters=[
            #             #     FilterACL(
            #             #         scope="payload",
            #             #         action="allow",
            #             #         field="not_a_real_name",
            #             #         match_regex="^not_a_real_pattern$",
            #             #     )
            #             # ],
            #         )
            #     ],
            # ),
        },
    )
    logging: LoggingSettings = LoggingSettings()

    model_config = SettingsConfigDict(extra="ignore")


def get_app_settings() -> AppSettings:
    """
    Dependency function to provide settings.

    Returns:
        AppSettings: The application settings.
    """
    return _settings


_config_data: dict = load_config(get_config_files())
_settings: AppSettings = AppSettings(**_config_data)
