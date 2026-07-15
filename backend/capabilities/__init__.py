from capabilities.schema import Capabilities, GpuCapability, ModelsCapability, OllamaCapability
from capabilities.ollama import detect_ollama

__all__ = [
    "Capabilities",
    "GpuCapability",
    "ModelsCapability",
    "OllamaCapability",
    "build_capabilities",
    "detect_ollama",
]


async def build_capabilities() -> Capabilities:
    ollama = await detect_ollama()
    return Capabilities(
        ollama=ollama,
        gpu=GpuCapability(
            available=None,
            name=None,
            note="detection deferred; see docs/learning-notes.md",
        ),
        models=ModelsCapability(chat=False, embedding=False),
    )
