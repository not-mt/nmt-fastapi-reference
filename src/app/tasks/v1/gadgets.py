# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Async tasks for gadget resources."""

import logging
import time

from huey.api import Task
from nmtfast.middleware.v1.request_id import REQUEST_ID_CONTEXTVAR
from nmtfast.tasks.v1.huey import fetch_task_metadata, store_task_metadata
from sqlalchemy.orm import Session

from app.core.v1.sqlalchemy import with_sync_session
from app.core.v1.tasks import huey_app
from app.models.v1.gadgets import Gadget
from app.schemas.v1.gadgets import GadgetZapTask

logger = logging.getLogger(__name__)


@huey_app.task(retries=3, retry_delay=5, context=True)
@with_sync_session
def gadget_zap_task(
    request_id: str,
    gadget_id: int,
    duration: int,
    task: Task,
    db_session: Session,
) -> GadgetZapTask:
    """
    Execute zap operation on a gadget using sync SQLAlchemy session.

    This task in a demonstration of how to run code in a Huey worker, using

    Args:
        request_id: Unique request ID that generated the task.
        gadget_id: Unique ID of the gadget to update.
        duration: Run the task for this many seconds.
        task: Huey task context (injected automatically).
        db_session: SQLAlchemy session (injected by @with_sync_session).

    Raises:
        AssertionError: Raised if db_gadget cannot be found, which should not
            be possible.

    Returns:
        GadgetZapTask: Information about about the newly created task.
    """
    REQUEST_ID_CONTEXTVAR.set(request_id)  # use same request ID from API caller
    task_uuid = task.id
    db_gadget = db_session.get(Gadget, gadget_id)
    assert db_gadget is not None, f"Gadget with ID {gadget_id} not found"
    logger.debug(f"{task_uuid}: db_gadget: {db_gadget}")

    # load the task as a pydantic model so we can validate
    task_md = GadgetZapTask.model_validate(
        fetch_task_metadata(huey_app, task_uuid),
    )
    task_md.state = "RUNNING"
    store_task_metadata(huey_app, task_uuid, task_md.model_dump())

    for tick in range(1, duration + 1):
        logger.debug(f"{task_uuid}: Running for {tick} of {duration}...")
        task_md.runtime = tick
        store_task_metadata(huey_app, task_uuid, task_md.model_dump())
        time.sleep(1)

    task_md.state = "SUCCESS"
    new_force = db_gadget.force + 1
    db_gadget.force = new_force
    db_session.commit()

    logger.info(f"{task_uuid}: Task complete! New db_gadget.force: {db_gadget.force}")
    store_task_metadata(huey_app, task_uuid, task_md.model_dump())

    return task_md
