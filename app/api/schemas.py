"""Strict evaluator-facing API schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConversationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str
    content: str

    @field_validator("role")
    @classmethod
    def role_must_be_supported(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"user", "assistant"}:
            raise ValueError("role must be user or assistant")
        return value

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("content must not be blank")
        return value


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[ConversationMessage] = Field(min_length=1)


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    url: str
    test_type: str

    @field_validator("name", "url", "test_type")
    @classmethod
    def recommendation_text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("recommendation fields must not be blank")
        return value


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reply: str
    recommendations: list[Recommendation] = Field(default_factory=list, max_length=10)
    end_of_conversation: bool = False

    @field_validator("reply")
    @classmethod
    def reply_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reply must not be blank")
        return value
