# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Dependencies related to authorization and authentication."""

import logging

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from nmtfast.auth.v1.api_keys import authenticate_api_key
from nmtfast.auth.v1.exceptions import AuthenticationError
from nmtfast.auth.v1.jwt import authenticate_token
from nmtfast.auth.v1.oauth import OAuth2ClientCredentials
from nmtfast.settings.v1.schemas import SectionACL

from app.core.v1.settings import AppSettings, get_app_settings

logger = logging.getLogger(__name__)

# NOTE: We load app settings here because loading OAuth2ClientCredentials with a custom
#   tokenUrl is very complicated to do with dependency injection, and not worth the
#   added complexity.
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)
oauth2_scheme = OAuth2ClientCredentials(
    tokenUrl=get_app_settings().auth.swagger_token_url,
    auto_error=False,
)


async def process_api_key_header(api_key: str, settings: AppSettings) -> str:
    """
    Authenticate using an API key.

    Args:
        api_key: The API key from the request header.
        settings: The application settings.

    Returns:
        str: Returns an informational string if authentication is successful.

    Raises:
        HTTPException: If the API key is not valid.
    """
    if api_key:
        try:
            acls = await authenticate_api_key(api_key, settings.auth)
            if acls:
                return "API key successfully authenticated."
        except AuthenticationError as exc:
            raise HTTPException(status_code=403, detail=f"Invalid API key: {exc}")

    # NOTE: this should never reached because authenticate_api_key will raise an
    #   exception if acls is empty, but it exists to prevent unauthorized access
    #   in the event that authenticate_api_key is bugged
    raise HTTPException(status_code=403, detail="Invalid API key (no permissions)")


async def process_bearer_token(token: str, settings: AppSettings) -> str:
    """
    Authenticate using a Bearer (JWT) token.

    Args:
        token: The OAuth2 token from the request header.
        settings: The application settings.

    Returns:
        str: Returns an informational string if authentication is successful.

    Raises:
        HTTPException: If the token is not valid.
    """
    if not token or not token.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header",
        )
    token = token.replace("Bearer ", "")
    if len(token.split(".")) != 3:
        raise HTTPException(status_code=403, detail="Invalid token")

    try:
        acls = await authenticate_token(token, settings.auth)
        if acls:
            return "Token successfully authenticated."
    except AuthenticationError as exc:
        raise HTTPException(status_code=403, detail=f"Invalid token: {exc}")

    # NOTE: this should never reached because authenticate_token will raise an
    #   exception if acls is empty, but it exists to prevent unauthorized access
    #   in the event that authenticate_token is bugged
    raise HTTPException(status_code=403, detail="Invalid client (no permissions)")


async def authenticate_headers(
    api_key: str = Security(api_key_header),
    token: str = Security(oauth2_scheme),
    settings: AppSettings = Depends(get_app_settings),
) -> str:
    """
    Authenticate client headers, which might be a Bearer token or an API key.

    Args:
        api_key: The API key from the request header.
        token: The API key from the request header.
        settings: The application settings.

    Returns:
        str: A string indicating which authentication method was used.

    Raises:
        HTTPException: If the API key is not valid.
    """
    # reject if both API key and token were provided
    if api_key and token:
        raise HTTPException(
            status_code=403,
            detail=(
                "Using an X-API-Key header and Bearer token are mutually exclusive."
            ),
        )

    # check API key authentication (if provided)
    if api_key:
        try:
            acls = await process_api_key_header(api_key, settings)
            if acls:
                return "API key successfully authenticated."
        except AuthenticationError as exc:
            raise HTTPException(status_code=403, detail=f"Invalid API key: {exc}")

        raise HTTPException(status_code=403, detail="API key authentication failed")

    # check tokenauthentication (if provided)
    if token:
        try:
            acls = await process_bearer_token(token, settings)
            if acls:
                return "Bearer token successfully authenticated."
        except AuthenticationError as exc:
            raise HTTPException(status_code=403, detail=f"Invalid token: {exc}")

    raise HTTPException(status_code=403, detail="Missing X-API-Key and Bearer token.")


async def get_acls(
    request: Request,
    settings: AppSettings = Depends(get_app_settings),
) -> list[SectionACL]:
    """
    Get ACLs for an API key or a JWT.

    Extracts either the API key or JWT token from the request, matches them
    against the ACL config, and returns the allowed ACLs.

    Args:
        request: The incoming request.
        settings: The application's Pydantic AppSettings object.

    Returns:
        list[SectionACL]: A list of ACLs associated with the client.

    Raises:
        HTTPException: If the client is unauthorized.
    """
    api_key = request.headers.get("X-API-Key")
    token = request.headers.get("Authorization")
    acls: list[SectionACL] = []

    # check API key authentication (if provided)
    if api_key:
        try:
            acls = await authenticate_api_key(api_key, settings.auth)
        except AuthenticationError as exc:
            raise HTTPException(status_code=403, detail=f"Invalid API key: {exc}")

    # check OAuth2 token authentication (if provided)
    elif token and token.startswith("Bearer "):
        token = token.replace("Bearer ", "")
        if len(token.split(".")) != 3:
            raise HTTPException(status_code=403, detail="Invalid token")

        try:
            acls = await authenticate_token(token, settings.auth)
        except AuthenticationError as exc:
            raise HTTPException(status_code=403, detail=f"Invalid token: {exc}")

    # if neither API key nor token are valid
    if not acls:
        raise HTTPException(status_code=403, detail="Unauthorized")

    return acls
