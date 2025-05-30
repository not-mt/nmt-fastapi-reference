# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""ORM model for gadget resources."""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.v1.sqlalchemy import Base


class Gadget(Base):
    """SQLAlchemy ORM model for gadgets."""

    __tablename__ = "gadgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    height: Mapped[str] = mapped_column(String(32), nullable=True)
    mass: Mapped[str] = mapped_column(String(32), nullable=True)
    force: Mapped[int] = mapped_column(Integer, nullable=True)
