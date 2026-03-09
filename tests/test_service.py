import asyncio

import pytest

from link_shortener.service import (
    LinkAlreadyExistsError,
    LinkNotFoundError,
    create_link,
    delete_link,
    get_link,
    list_links,
    update_link,
)


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
        page_size = 2
        cursor = options.get("cursor")
        start_index = 0

        if cursor:
            try:
                start_index = keys.index(cursor) + 1
            except ValueError:
                start_index = len(keys)

        page = keys[start_index : start_index + page_size]
        list_complete = start_index + page_size >= len(keys)
        next_cursor = page[-1] if (page and not list_complete) else ""

        return {
            "keys": [{"name": key} for key in page],
            "list_complete": list_complete,
            "cursor": next_cursor,
        }


class NullProxy:
    def to_py(self):
        return None


def test_create_link_with_custom_code():
    kv = FakeKV()
    result = asyncio.run(create_link(kv, code="abc123", link="https://example.com"))
    assert result.code == "abc123"
    assert result.link == "https://example.com"
    assert kv.store["abc123"] == "https://example.com"


def test_create_link_conflict_raises():
    kv = FakeKV()
    kv.store["abc123"] = "https://old.example.com"

    with pytest.raises(LinkAlreadyExistsError):
        asyncio.run(create_link(kv, code="abc123", link="https://new.example.com"))


def test_create_link_generates_code(monkeypatch):
    kv = FakeKV()
    monkeypatch.setattr("link_shortener.service.generate_code", lambda: "xy123")
    result = asyncio.run(create_link(kv, link="https://example.com"))
    assert result.code == "xy123"


def test_get_update_delete_link_flow():
    kv = FakeKV()
    kv.store["abc123"] = "https://example.com"

    got = asyncio.run(get_link(kv, "abc123"))
    assert got.link == "https://example.com"

    updated = asyncio.run(update_link(kv, "abc123", "https://example.com/new"))
    assert updated.link.endswith("/new")

    asyncio.run(delete_link(kv, "abc123"))
    assert "abc123" not in kv.store


def test_missing_link_errors():
    kv = FakeKV()
    with pytest.raises(LinkNotFoundError):
        asyncio.run(get_link(kv, "missing"))
    with pytest.raises(LinkNotFoundError):
        asyncio.run(update_link(kv, "missing", "https://example.com"))
    with pytest.raises(LinkNotFoundError):
        asyncio.run(delete_link(kv, "missing"))


def test_create_link_treats_js_null_as_missing():
    kv = FakeKV()

    async def missing_get(key: str):
        return NullProxy() if key not in kv.store else kv.store[key]

    kv.get = missing_get

    result = asyncio.run(create_link(kv, code="abc123", link="https://example.com"))

    assert result.code == "abc123"
    assert kv.store["abc123"] == "https://example.com"


def test_get_link_treats_js_null_as_missing():
    kv = FakeKV()

    async def missing_get(key: str):
        return NullProxy()

    kv.get = missing_get

    with pytest.raises(LinkNotFoundError):
        asyncio.run(get_link(kv, "missing"))


def test_list_links_paginates_and_returns_sorted():
    kv = FakeKV()
    kv.store = {
        "zzz": "https://z.example.com",
        "aaa": "https://a.example.com",
        "m42": "https://m.example.com",
    }

    results = asyncio.run(list_links(kv))
    assert [item.code for item in results] == ["aaa", "m42", "zzz"]
