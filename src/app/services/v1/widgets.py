# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Business logic for widget resources."""

import logging

from nmtfast.auth.v1.acl import check_acl
from nmtfast.auth.v1.exceptions import AuthorizationError

from app.core.v1.settings import AppSettings
from app.errors.v1.exceptions import NotFoundError
from app.repositories.v1.widgets import WidgetRepositoryProtocol
from app.schemas.v1.widgets import WidgetCreate, WidgetRead

logger = logging.getLogger(__name__)


class WidgetService:
    """
    Service layer for widget business logic.

    Args:
        widget_repository: The repository for widget data operations.
        acls: List of ACLs associated with authenticated client/apikey.
        settings: The application's AppSettings object.
    """

    def __init__(
        self,
        widget_repository: WidgetRepositoryProtocol,
        acls: list,
        settings: AppSettings,
    ) -> None:
        self.widget_repository: WidgetRepositoryProtocol = widget_repository
        self.acls = acls
        self.settings = settings

    async def _is_authz(self, acls: list, permission: str) -> None:
        """
        Check if the ACLs allow access to the given resource.

        Args:
            acls: List of ACLs associated with this client
            permission: Required in order to complete the requested operation.

        Raises:
            AuthorizationError:
        """
        if not await check_acl("widgets", acls, permission):
            raise AuthorizationError("Not authorized to '{permission}'")

    async def create_widget(self, input_widget: WidgetCreate) -> WidgetRead:
        """
        Create a new widget.

        Args:
            input_widget: The widget data provided by the client.

        Returns:
            WidgetRead: The newly created widget as a Pydantic model.
        """
        await self._is_authz(self.acls, "create")
        db_widget = await self.widget_repository.create_widget(input_widget)

        return WidgetRead.model_validate(db_widget)

    async def get_widget_by_id(self, widget_id: int) -> WidgetRead:
        """
        Retrieve a widget by its ID.

        Args:
            widget_id: The ID of the widget to retrieve.

        Raises:
            NotFoundError: If the widget is not found.

        Returns:
            WidgetRead: The retrieved widget.
        """
        await self._is_authz(self.acls, "read")
        db_widget = await self.widget_repository.get_by_id(widget_id)

        if not db_widget:
            raise NotFoundError(widget_id, "Widget")

        return WidgetRead.model_validate(db_widget)
