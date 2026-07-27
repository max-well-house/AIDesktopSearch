from capabilities.schema import (
    Capabilities,
    GpuCapability,
    ModelsCapability,
    OllamaCapability,
    VectorStoreCapability,
)
from capabilities.ollama import detect_ollama
from embeddings.store import vector_store_status

__all__ = [
    "Capabilities",
    "GpuCapability",
    "ModelsCapability",
    "OllamaCapability",
    "VectorStoreCapability",
    "build_capabilities",
    "detect_ollama",
]


async def build_capabilities() -> Capabilities:
    ollama = await detect_ollama()
    vs = vector_store_status()
    return Capabilities(
        ollama=ollama,
        gpu=GpuCapability(
            available=None,
            name=None,
            note="detection deferred; see docs/learning-notes.md",
        ),
        models=ModelsCapability(chat=False, embedding=False),
        vector_store=VectorStoreCapability(
            available=bool(vs.get("available")),
            version=vs.get("version"),
            note=vs.get("note"),
            dimension=int(vs.get("dimension") or 768),
            chunk_count=int(vs.get("chunk_count") or 0),
        ),
    )
