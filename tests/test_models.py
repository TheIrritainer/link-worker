import pytest
from pydantic import ValidationError

from link_shortener.models import LinkCreateRequest, LinkRecord, LinkUpdateRequest, is_valid_code


def test_code_validator_accepts_lowercase_alphanumeric():
    assert is_valid_code("abc123")
    assert is_valid_code("a1")


def test_code_validator_rejects_uppercase_or_symbols():
    assert not is_valid_code("ABC")
    assert not is_valid_code("bad-code")
    assert not is_valid_code("waytoolongcode1")


def test_link_record_validation_rules():
    model = LinkRecord(code="abc123", link="https://example.com")
    assert model.code == "abc123"
    assert model.link == "https://example.com"

    with pytest.raises(ValidationError):
        LinkRecord(code="ABC123", link="https://example.com")

    with pytest.raises(ValidationError):
        LinkRecord(code="abc123", link="x" * 1025)

    with pytest.raises(ValidationError):
        LinkRecord(code="abc123", link="javascript:null")

    with pytest.raises(ValidationError):
        LinkRecord(code="abc123", link="/relative/path")


def test_create_request_allows_missing_code():
    payload = LinkCreateRequest(link="https://example.com")
    assert payload.code is None
    assert payload.link == "https://example.com"


def test_update_request_validation():
    payload = LinkUpdateRequest(link="https://example.com/new")
    assert payload.link.endswith("/new")

    with pytest.raises(ValidationError):
        LinkUpdateRequest(link="")

    with pytest.raises(ValidationError):
        LinkUpdateRequest(link="data:text/plain,hello")

    with pytest.raises(ValidationError):
        LinkUpdateRequest(link="example.com/no-scheme")


def test_create_request_rejects_non_http_targets():
    with pytest.raises(ValidationError):
        LinkCreateRequest(link="javascript:null")

    with pytest.raises(ValidationError):
        LinkCreateRequest(link="/jsnull")
