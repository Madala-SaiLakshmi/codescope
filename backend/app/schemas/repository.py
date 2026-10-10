from datetime import datetime
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RepositoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_type: Literal["git_url"] = "git_url"
    source_url: str = Field(max_length=500)
    default_branch: str = Field(default="main", max_length=100)

    @field_validator("source_url")
    @classmethod
    def must_be_https(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("source_url must be an https:// URL")
        return v


class RepositoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    source_type: str
    source_url: str | None
    default_branch: str
    created_at: datetime