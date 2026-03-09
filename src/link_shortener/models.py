import re
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import BaseModel, StringConstraints, field_validator

CODE_PATTERN = r"^[a-z0-9]{1,12}$"
LINK_MAX_LENGTH = 1024

CodeStr = Annotated[str, StringConstraints(pattern=CODE_PATTERN, max_length=12)]
LinkStr = Annotated[str, StringConstraints(min_length=1, max_length=LINK_MAX_LENGTH)]


def is_valid_code(value: str) -> bool:
    return re.fullmatch(CODE_PATTERN, value) is not None


def is_valid_redirect_link(value: str) -> bool:
    parsed = urlsplit(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_redirect_link(value: str) -> str:
    if not is_valid_redirect_link(value):
        raise ValueError("link must be an absolute http(s) URL")
    return value


class LinkRecord(BaseModel):
    code: CodeStr
    link: LinkStr

    @field_validator("link")
    @classmethod
    def validate_link(cls, value: str) -> str:
        return validate_redirect_link(value)


class LinkCreateRequest(BaseModel):
    code: CodeStr | None = None
    link: LinkStr

    @field_validator("link")
    @classmethod
    def validate_link(cls, value: str) -> str:
        return validate_redirect_link(value)


class LinkUpdateRequest(BaseModel):
    link: LinkStr

    @field_validator("link")
    @classmethod
    def validate_link(cls, value: str) -> str:
        return validate_redirect_link(value)
