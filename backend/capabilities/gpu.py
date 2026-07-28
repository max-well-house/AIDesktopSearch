"""NVIDIA-first GPU capability probe for /health (issue #112).

Detection uses nvidia-smi when present. Other vendors stay available=null
until a later probe; feature gates must use gpu_preferred() only — never
branch on device name strings (Decision #003 rule 9).
"""

from __future__ import annotations

import subprocess
import sys

from capabilities.schema import GpuCapability

PROBE_TIMEOUT_SECONDS = 1.5

_NOTE_PREFERRED = "GPU preferred for Ollama"
_NOTE_UNAVAILABLE = "No NVIDIA GPU detected — CPU / no GPU preference"
_NOTE_UNKNOWN = (
    "NVIDIA-first detection; nvidia-smi not available — unknown on other vendors"
)


def gpu_preferred(gpu: GpuCapability) -> bool:
    """Capability gate: True only when GPU availability is known True."""
    return gpu.available is True


def _subprocess_kwargs() -> dict:
    kwargs: dict = {
        "capture_output": True,
        "text": True,
        "timeout": PROBE_TIMEOUT_SECONDS,
        "check": False,
    }
    if sys.platform == "win32":
        # Avoid flashing a console window during /health probes.
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return kwargs


def detect_gpu() -> GpuCapability:
    """Probe GPU without raising — missing tooling is a capability signal."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name",
                "--format=csv,noheader",
            ],
            **_subprocess_kwargs(),
        )
    except FileNotFoundError:
        return GpuCapability(available=None, name=None, note=_NOTE_UNKNOWN)
    except subprocess.TimeoutExpired:
        return GpuCapability(available=None, name=None, note=_NOTE_UNKNOWN)
    except OSError:
        return GpuCapability(available=None, name=None, note=_NOTE_UNKNOWN)

    if result.returncode != 0:
        return GpuCapability(
            available=False,
            name=None,
            note=_NOTE_UNAVAILABLE,
        )

    names = [
        line.strip()
        for line in (result.stdout or "").splitlines()
        if line.strip()
    ]
    if not names:
        return GpuCapability(
            available=False,
            name=None,
            note=_NOTE_UNAVAILABLE,
        )

    gpu = GpuCapability(
        available=True,
        name=names[0],
        note=None,
    )
    # Gate uses available only — name is display-only.
    gpu.note = _NOTE_PREFERRED if gpu_preferred(gpu) else _NOTE_UNAVAILABLE
    return gpu
