# -*- coding: utf-8 -*-
# Copyright (c) 2024. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Pydantic schema for widgets."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class WidgetBase(BaseModel):
    """Base schema for widgets."""

    name: str = Field(..., description="Name of the widget.")
    height: Optional[str] = Field(None, description="Height of the widget (optional).")
    mass: Optional[str] = Field(None, description="Mass of the widget (optional).")
    force: Optional[int] = Field(
        None, description="Force applied to the widget (optional)."
    )


class WidgetCreate(WidgetBase):
    """Schema for creating a new widget."""

    pass


class WidgetRead(WidgetBase):
    """Schema for reading a widget, including additional attributes."""

    id: int = Field(..., description="Database ID of the widget.")
    model_config = ConfigDict(from_attributes=True)


class WidgetUpdate(BaseModel):
    """
    Schema for updating an existing widget.

    All fields are optional to support partial updates.
    """

    name: Optional[str] = Field(None, description="Name of the widget.")
    height: Optional[str] = Field(None, description="Height of the widget (optional).")
    mass: Optional[str] = Field(None, description="Mass of the widget (optional).")
    force: Optional[int] = Field(
        None, description="Force applied to the widget (optional)."
    )


class WidgetBulkUpdate(BaseModel):
    """
    Schema for bulk updating multiple widgets.

    Contains a list of widget IDs and the partial update data
    to apply to all of them.
    """

    ids: list[int] = Field(..., description="List of widget IDs to update.")
    updates: WidgetUpdate = Field(..., description="Partial update data to apply.")


class WidgetZap(BaseModel):
    """Schema to initiate zap task on a widget."""

    duration: int = Field(10, description="Duration of the zap in seconds.")


class WidgetZapTask(BaseModel):
    """Base schema for widgets."""

    uuid: str = Field(..., description="UUID of the zap task.")
    state: str = Field("UNKNOWN", description="Current state of the zap task.")
    id: int = Field(..., description="ID of the widget associated with the task.")
    duration: int = Field(
        ..., description="Requested duration for the task in seconds."
    )
    runtime: int = Field(..., description="Runtime of the task in seconds.")
