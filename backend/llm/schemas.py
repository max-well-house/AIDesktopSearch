"""API models for local chat (#70)."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    system: str | None = None


class ChatResponse(BaseModel):
    reply: str
    model: str
