# -*- coding: utf-8 -*-
# Copyright (c) 2024. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Pydantic schema for gadgets."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


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
    """Base schema for gadgets."""

    uuid: str = Field(..., description="UUID of the zap task.")
    state: str = Field("UNKNOWN", description="Current state of the zap task.")
    id: str = Field(..., description="ID of the gadget associated with the task.")
    duration: int = Field(
        ..., description="Requested duration for the task in seconds."
    )
    runtime: int = Field(..., description="Runtime of the task in seconds.")
