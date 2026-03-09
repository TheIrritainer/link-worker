import secrets
import string
from typing import Any, Protocol

from link_shortener.models import LinkRecord

try:
    from pyodide.ffi import jsnull
except ImportError:
    jsnull = None

ALPHABET = string.ascii_lowercase + string.digits
DEFAULT_CODE_LENGTH = 7
MAX_GENERATION_ATTEMPTS = 16


class KVStore(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def put(self, key: str, value: str) -> None: ...

    async def delete(self, key: str) -> None: ...

    async def list(self, options: dict[str, str] | None = None) -> Any: ...


class LinkAlreadyExistsError(Exception):
    pass


class LinkNotFoundError(Exception):
    pass


def generate_code(length: int = DEFAULT_CODE_LENGTH) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def _to_python(value: Any) -> Any:
    if hasattr(value, "to_py"):
        try:
            return value.to_py()
        except Exception:
            return value
    return value


def _normalize_kv_value(value: Any) -> str | None:
    value = _to_python(value)

    if value is None or value is jsnull:
        return None

    if isinstance(value, str):
        return value

    return str(value)


def _normalize_keys(raw_keys: Any) -> list[str]:
    raw_keys = _to_python(raw_keys)
    keys: list[str] = []

    for item in raw_keys or []:
        normalized_item = _to_python(item)
        if isinstance(normalized_item, dict):
            name = normalized_item.get("name")
        else:
            name = getattr(normalized_item, "name", None)
        if isinstance(name, str) and name:
            keys.append(name)

    return keys


def _normalize_list_payload(payload: Any) -> tuple[list[str], str | None, bool]:
    payload = _to_python(payload)

    if isinstance(payload, dict):
        raw_keys = payload.get("keys", [])
        cursor = payload.get("cursor") or None
        is_complete = bool(payload.get("list_complete", True))
        return _normalize_keys(raw_keys), cursor, is_complete

    raw_keys = getattr(payload, "keys", [])
    cursor = getattr(payload, "cursor", None) or None
    is_complete = bool(getattr(payload, "list_complete", True))
    return _normalize_keys(raw_keys), cursor, is_complete


async def _generate_unique_code(
    kv: KVStore, code_factory=None, max_attempts: int = MAX_GENERATION_ATTEMPTS
) -> str:
    if code_factory is None:
        code_factory = generate_code

    for _ in range(max_attempts):
        candidate = code_factory()
        if _normalize_kv_value(await kv.get(candidate)) is None:
            return candidate

    raise RuntimeError("Failed to generate a unique short code")


async def create_link(kv: KVStore, link: str, code: str | None = None) -> LinkRecord:
    resolved_code = code

    if resolved_code is None:
        resolved_code = await _generate_unique_code(kv)
    elif _normalize_kv_value(await kv.get(resolved_code)) is not None:
        raise LinkAlreadyExistsError(resolved_code)

    await kv.put(resolved_code, link)
    return LinkRecord(code=resolved_code, link=link)


async def get_link(kv: KVStore, code: str) -> LinkRecord:
    link = _normalize_kv_value(await kv.get(code))
    if link is None:
        raise LinkNotFoundError(code)
    return LinkRecord(code=code, link=link)


async def update_link(kv: KVStore, code: str, link: str) -> LinkRecord:
    if _normalize_kv_value(await kv.get(code)) is None:
        raise LinkNotFoundError(code)

    await kv.put(code, link)
    return LinkRecord(code=code, link=link)


async def delete_link(kv: KVStore, code: str) -> None:
    if _normalize_kv_value(await kv.get(code)) is None:
        raise LinkNotFoundError(code)

    await kv.delete(code)


async def list_links(kv: KVStore) -> list[LinkRecord]:
    cursor: str | None = None
    records: list[LinkRecord] = []

    while True:
        if cursor:
            payload = await kv.list({"cursor": cursor})
        else:
            payload = await kv.list()

        keys, next_cursor, is_complete = _normalize_list_payload(payload)
        for code in keys:
            link = _normalize_kv_value(await kv.get(code))
            if link is not None:
                records.append(LinkRecord(code=code, link=link))

        if is_complete or not next_cursor:
            break
        cursor = next_cursor

    records.sort(key=lambda item: item.code)
    return records
