# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""ORM model for widget resources."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.v1.sqlalchemy import Base


class Widget(Base):
    """SQLAlchemy ORM model for widgets."""

    __tablename__ = "widgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    height: Mapped[str] = mapped_column(String(32), nullable=True)
    mass: Mapped[str] = mapped_column(String(32), nullable=True)
    force: Mapped[int] = mapped_column(Integer, nullable=True)
    last_task_uuid: Mapped[str | None] = mapped_column(
        String(36), nullable=True, default=None
    )
    last_task_status: Mapped[str | None] = mapped_column(
        String(16), nullable=True, default=None
    )
    zap_tasks: Mapped[list["WidgetZapTask"]] = relationship(
        "WidgetZapTask", back_populates="widget", cascade="all, delete-orphan"
    )


class WidgetZapTask(Base):
    """ORM model for persisted zap task records."""

    __tablename__ = "widget_zap_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    widget_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("widgets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    duration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    runtime: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    widget: Mapped["Widget"] = relationship("Widget", back_populates="zap_tasks")
