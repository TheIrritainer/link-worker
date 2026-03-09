import asyncio

import pytest
from fastapi import HTTPException, Response

from app import create_shortlink, get_shortlink, resolve_shortlink
from link_shortener.models import LinkCreateRequest


class FakeKV:
    def __init__(self):
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def put(self, key: str, value: str) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)

    async def list(self, options: dict[str, str] | None = None):
        options = options or {}
        keys = sorted(self.store.keys())
        return {
            "keys": [{"name": key} for key in keys],
            "list_complete": True,
            "cursor": "",
        }


class NullProxy:
    def to_py(self):
        return None


class FakeEnv:
    DOMAIN_NAME = "go.example.com"
    STATIC_ACCESS_TOKEN = "token"

    def __init__(self):
        self.LINKS = FakeKV()


class FakeRequest:
    def __init__(self, env):
        self.scope = {"env": env}


def test_resolve_shortlink_redirects_to_absolute_http_target():
    env = FakeEnv()
    env.LINKS.store["test"] = "https://example.com"
    request = FakeRequest(env)
    response = asyncio.run(resolve_shortlink("test", request))

    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com"


def test_resolve_shortlink_rejects_invalid_target_from_kv():
    env = FakeEnv()
    env.LINKS.store["test"] = "javascript:null"
    request = FakeRequest(env)

    with pytest.raises(HTTPException) as error:
        asyncio.run(resolve_shortlink("test", request))
    assert error.value.status_code == 404


def test_create_shortlink_accepts_unused_code_when_missing_kv_value_is_js_null():
    env = FakeEnv()
    request = FakeRequest(env)
    response = Response()

    async def missing_get(key: str):
        return NullProxy() if key not in env.LINKS.store else env.LINKS.store[key]

    env.LINKS.get = missing_get
    created = asyncio.run(
        create_shortlink(
            request,
            LinkCreateRequest(code="fresh123", link="https://example.com"),
            response,
        )
    )

    assert created.model_dump() == {"code": "fresh123", "link": "https://example.com"}
    assert env.LINKS.store["fresh123"] == "https://example.com"
    assert response.headers["location"] == "https://go.example.com/fresh123"


def test_get_shortlink_returns_404_when_missing_kv_value_is_js_null():
    env = FakeEnv()
    request = FakeRequest(env)

    async def missing_get(key: str):
        return NullProxy()

    env.LINKS.get = missing_get

    with pytest.raises(HTTPException) as error:
        asyncio.run(get_shortlink("missing123", request))

    assert error.value.status_code == 404
    assert error.value.detail == "Shortlink not found"
