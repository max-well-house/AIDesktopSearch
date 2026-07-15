import os
import shutil
from pathlib import Path

import httpx

from capabilities.schema import OllamaCapability

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
PROBE_TIMEOUT_SECONDS = 2.0


def _ollama_binary_present() -> bool:
    if shutil.which("ollama"):
        return True

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates = [
            Path(local_app_data) / "Programs" / "Ollama" / "ollama.exe",
            Path(local_app_data) / "Programs" / "Ollama" / "ollama.app.exe",
        ]
        if any(path.is_file() for path in candidates):
            return True

    program_files = os.environ.get("ProgramFiles")
    if program_files:
        candidate = Path(program_files) / "Ollama" / "ollama.exe"
        if candidate.is_file():
            return True

    return False


async def detect_ollama(base_url: str = OLLAMA_BASE_URL) -> OllamaCapability:
    """Probe Ollama without raising — missing/stopped is a capability signal."""
    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_SECONDS) as client:
            response = await client.get(f"{base_url.rstrip('/')}/api/version")
            response.raise_for_status()
            payload = response.json()
            version = payload.get("version") if isinstance(payload, dict) else None
            return OllamaCapability(
                available=True,
                status="available",
                version=str(version) if version is not None else None,
                base_url=base_url,
            )
    except Exception:
        if _ollama_binary_present():
            return OllamaCapability(
                available=False,
                status="unavailable",
                version=None,
                base_url=base_url,
            )
        return OllamaCapability(
            available=False,
            status="not_installed",
            version=None,
            base_url=base_url,
        )
