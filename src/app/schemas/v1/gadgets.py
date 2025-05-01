# -*- coding: utf-8 -*-
# Copyright (c) 2024. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Pydantic schema for gadgets."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class GadgetBase(BaseModel):
    """Base schema for gadgets."""

    name: str
    height: Optional[str] = None
    mass: Optional[str] = None
    force: Optional[int] = None


class GadgetCreate(GadgetBase):
    """Schema for creating a new gadget."""

    pass


class GadgetRead(GadgetBase):
    """Schema for reading a gadget, including additional attributes."""

    id: int
    model_config = ConfigDict(from_attributes=True)


class GadgetZap(BaseModel):
    """Schema to initiate zap task on a gadget."""

    duration: int = 10


class GadgetZapTask(BaseModel):
    """Base schema for gadgets."""

    uuid: str
    state: str = "UNKNOWN"
    id: int
    duration: int
    runtime: int
