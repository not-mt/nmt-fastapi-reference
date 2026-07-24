# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for gadget schema DTOs."""

from bson import ObjectId

from app.schemas.dto.v1.gadgets import GadgetZapTaskRecord


def test_gadget_zap_task_record_objectid_validator():
    """
    Test that GadgetZapTaskRecord converts ObjectId to string for the _id field.
    """
    oid = ObjectId("507f1f77bcf86cd799439011")
    result = GadgetZapTaskRecord(
        _id=oid,
        gadget_id="test",
        task_uuid="test-uuid",
    )

    assert result.id == "507f1f77bcf86cd799439011"
