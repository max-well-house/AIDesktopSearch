from typing import Literal

from pydantic import BaseModel, Field


OllamaStatus = Literal["available", "unavailable", "not_installed"]


class OllamaCapability(BaseModel):
    available: bool
    status: OllamaStatus
    version: str | None = None
    base_url: str = "http://127.0.0.1:11434"


class GpuCapability(BaseModel):
    available: bool | None = None
    name: str | None = None
    note: str | None = None


class ModelsCapability(BaseModel):
    chat: bool = False
    embedding: bool = False


class Capabilities(BaseModel):
    ollama: OllamaCapability
    gpu: GpuCapability = Field(default_factory=GpuCapability)
    models: ModelsCapability = Field(default_factory=ModelsCapability)


class HealthResponse(BaseModel):
    status: Literal["healthy"] = "healthy"
    version: str
    timestamp: str
    capabilities: Capabilities
