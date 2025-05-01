# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Async tasks for gadget resources."""

import logging
import time

from huey.api import Task
from nmtfast.middleware.v1.request_id import REQUEST_ID_CONTEXTVAR
from nmtfast.tasks.v1.huey import fetch_task_metadata, store_task_metadata
from pymongo.database import Database

from app.core.v1.mongo import with_sync_mongo_db
from app.core.v1.tasks import huey_app
from app.schemas.v1.gadgets import GadgetZapTask

logger = logging.getLogger(__name__)


@huey_app.task(retries=3, retry_delay=5, context=True)
@with_sync_mongo_db()
def gadget_zap_task(
    request_id: str,
    gadget_id: str,
    duration: int,
    task: Task,
    mongo_db: Database,
) -> GadgetZapTask:
    """
    Execute zap operation on a gadget using sync MongoDB client.

    This task in a demonstration of how to run code in a Huey worker.

    Args:
        request_id: Unique request ID that generated the task.
        gadget_id: Unique ID of the gadget to update.
        duration: Run the task for this many seconds.
        task: Huey task context (injected automatically).
        mongo_db: sync pymongo client (injected by @with_sync_mongo_db).

    Raises:
        AssertionError: Raised if db_gadget cannot be found, which should not
            be possible.

    Returns:
        GadgetZapTask: Information about about the newly created task.
    """
    REQUEST_ID_CONTEXTVAR.set(request_id)
    task_uuid = task.id

    # TODO: look at using repository to fetch from DB
    collection = mongo_db["gadgets"]
    db_gadget = collection.find_one({"id": gadget_id})
    assert db_gadget, f"Gadget with ID {gadget_id} not found"
    logger.debug(f"{task_uuid}: gadget: {db_gadget}")

    task_md = GadgetZapTask.model_validate(fetch_task_metadata(huey_app, task_uuid))
    task_md.state = "RUNNING"
    store_task_metadata(huey_app, task_uuid, task_md.model_dump())

    for tick in range(1, duration + 1):
        logger.debug(f"{task_uuid}: Running for {tick} of {duration}...")
        task_md.runtime = tick
        store_task_metadata(huey_app, task_uuid, task_md.model_dump())
        time.sleep(1)

    # TODO: look at using repository to update resource in DB
    task_md.state = "SUCCESS"
    new_force = (db_gadget.get("force") or 0) + 1
    collection.update_one({"id": gadget_id}, {"$set": {"force": new_force}})
    logger.info(f"{task_uuid}: Task complete! New force: {new_force}")
    store_task_metadata(huey_app, task_uuid, task_md.model_dump())

    return task_md
