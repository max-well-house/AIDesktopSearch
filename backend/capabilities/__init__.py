from capabilities.schema import (
    Capabilities,
    GpuCapability,
    ModelsCapability,
    OllamaCapability,
    VectorStoreCapability,
)
from capabilities.gpu import detect_gpu, gpu_preferred
from capabilities.ollama import detect_ollama
from embeddings.store import vector_store_status

__all__ = [
    "Capabilities",
    "GpuCapability",
    "ModelsCapability",
    "OllamaCapability",
    "VectorStoreCapability",
    "build_capabilities",
    "detect_gpu",
    "detect_ollama",
    "gpu_preferred",
]


async def build_capabilities() -> Capabilities:
    ollama = await detect_ollama()
    gpu = detect_gpu()
    vs = vector_store_status()
    # Lazy import avoids capabilities ↔ embeddings.client cycle at startup.
    from embeddings.client import model_available
    from embeddings.store import DEFAULT_EMBED_MODEL

    embedding_ready = bool(ollama.available) and model_available(DEFAULT_EMBED_MODEL)
    from llm.client import DEFAULT_CHAT_MODEL, chat_model_available

    chat_ready = bool(ollama.available) and chat_model_available(DEFAULT_CHAT_MODEL)
    return Capabilities(
        ollama=ollama,
        gpu=gpu,
        models=ModelsCapability(chat=chat_ready, embedding=embedding_ready),
        vector_store=VectorStoreCapability(
            available=bool(vs.get("available")),
            version=vs.get("version"),
            note=vs.get("note"),
            dimension=int(vs.get("dimension") or 768),
            chunk_count=int(vs.get("chunk_count") or 0),
        ),
    )
