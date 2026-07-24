# -*- coding: utf-8 -*-
# Copyright (c) 2024. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Pydantic schema for gadgets."""

from datetime import datetime
from typing import Any, Optional

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator


class GadgetBase(BaseModel):
    """Base schema for gadgets."""

    name: str = Field(..., description="Name of the gadget.")
    height: Optional[str] = Field(None, description="Height of the gadget (optional).")
    mass: Optional[str] = Field(None, description="Mass of the gadget (optional).")
    force: Optional[int] = Field(
        None, description="Force applied to the gadget (optional)."
    )


class GadgetCreate(GadgetBase):
    """Schema for creating a new gadget."""

    pass


class GadgetRead(GadgetBase):
    """Schema for reading a gadget, including additional attributes."""

    id: str = Field(..., description="Database or unique ID of the gadget.")
    last_task_uuid: str | None = Field(
        None, description="UUID of the most recent zap task."
    )
    last_task_status: str | None = Field(
        None, description="Status of the most recent zap task."
    )
    model_config = ConfigDict(from_attributes=True)


class GadgetUpdate(BaseModel):
    """
    Schema for updating an existing gadget.

    All fields are optional to support partial updates.
    """

    name: Optional[str] = Field(None, description="Name of the gadget.")
    height: Optional[str] = Field(None, description="Height of the gadget (optional).")
    mass: Optional[str] = Field(None, description="Mass of the gadget (optional).")
    force: Optional[int] = Field(
        None, description="Force applied to the gadget (optional)."
    )


class GadgetBulkUpdate(BaseModel):
    """
    Schema for bulk updating multiple gadgets.

    Contains a list of gadget IDs and the partial update data
    to apply to all of them.
    """

    ids: list[str] = Field(..., description="List of gadget IDs to update.")
    updates: GadgetUpdate = Field(..., description="Partial update data to apply.")


class GadgetZap(BaseModel):
    """Schema to initiate zap task on a gadget."""

    duration: int = Field(10, description="Duration of the zap in seconds.")


class GadgetZapTask(BaseModel):
    """
    DTO schema for gadget zap task metadata returned by Huey tasks.

    Used for task status updates and metadata storage.
    """

    uuid: str = Field(..., description="UUID of the zap task.")
    state: str = Field("UNKNOWN", description="Current state of the zap task.")
    gadget_id: str = Field(
        ..., description="ID of the gadget associated with the task."
    )
    duration: int = Field(
        ..., description="Requested duration for the task in seconds."
    )
    runtime: int = Field(..., description="Runtime of the task in seconds.")
    result: Optional[dict] = Field(None, description="Result data from the task.")


class GadgetZapTaskRecord(BaseModel):
    """Pydantic model for gadget zap task MongoDB document."""

    id: Optional[str] = Field(default=None, alias="_id")

    @field_validator("id", mode="before")
    @classmethod
    def convert_object_id(cls, value: Any) -> str | Any:
        """
        Convert ObjectId to string for MongoDB _id field.

        Args:
            value: The value to convert, which may be an ObjectId or already a string.

        Returns:
            str | Any: String representation of ObjectId, or the original value.
        """
        if isinstance(value, ObjectId):
            return str(value)
        return value

    gadget_id: str = Field(..., description="ID of the gadget.")
    task_uuid: str = Field(..., description="UUID of the zap task.")
    state: str = Field("PENDING", description="Current state of the zap task.")
    duration: int = Field(0, description="Duration of the task in seconds.")
    runtime: int = Field(0, description="Runtime of the task in seconds.")
    result: Optional[dict] = Field(None, description="Result data from the task.")
    created_at: Optional[datetime] = Field(
        None, description="Timestamp when the task record was created."
    )
    updated_at: Optional[datetime] = Field(
        None, description="Timestamp when the task record was last updated."
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class GadgetZapTaskRead(BaseModel):
    """Schema for a persisted gadget zap task history record."""

    task_uuid: str = Field(..., description="UUID of the zap task.")
    state: str = Field("UNKNOWN", description="Current state of the zap task.")
    gadget_id: str = Field(
        ..., description="ID of the gadget associated with the task."
    )
    duration: int = Field(
        ..., description="Requested duration for the task in seconds."
    )
    runtime: int = Field(..., description="Runtime of the task in seconds.")
    result: dict | None = Field(
        None, description="Result data from the task execution."
    )
    created_at: datetime | None = Field(
        None, description="Timestamp when the task record was created."
    )
    updated_at: datetime | None = Field(
        None, description="Timestamp when the task record was last updated."
    )

    model_config = ConfigDict(from_attributes=True)


class GadgetZapTaskListResponse(BaseModel):
    """Response containing a paginated list of gadget zap task history records."""

    tasks: list[GadgetZapTaskRead] = Field(
        ..., description="List of gadget zap task history records."
    )
    total: int = Field(..., description="Total number of task records.")
