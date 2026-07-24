# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Unit tests for MongoDB client setup."""


def test_get_async_client_empty_url(monkeypatch):
    """
    Test that get_async_client returns None when mongo.url is falsy.
    """
    from app.core.v1 import mongo as mongo_module

    monkeypatch.setattr(
        mongo_module.settings, "mongo", type("MongoSettings", (), {"url": ""})()
    )
    monkeypatch.setattr(mongo_module, "async_client", None)

    result = mongo_module.get_async_client()

    assert result is None


def test_get_sync_client_empty_url(monkeypatch):
    """
    Test that get_sync_client returns None when mongo.url is falsy.
    """
    from app.core.v1 import mongo as mongo_module

    monkeypatch.setattr(
        mongo_module.settings, "mongo", type("MongoSettings", (), {"url": ""})()
    )
    monkeypatch.setattr(mongo_module, "sync_client", None)

    result = mongo_module.get_sync_client()

    assert result is None
