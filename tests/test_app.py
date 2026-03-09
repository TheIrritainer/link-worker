import asyncio

import pytest
from fastapi import HTTPException

from app import resolve_shortlink


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
