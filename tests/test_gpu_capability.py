"""Unit tests for NVIDIA-first GPU capability detection (mocked subprocess)."""

from unittest.mock import MagicMock, patch

import subprocess

from capabilities.gpu import detect_gpu, gpu_preferred
from capabilities.schema import GpuCapability


def test_gpu_available_sets_name_and_preferred():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "NVIDIA GeForce RTX 5060 Ti\n"

    with patch("capabilities.gpu.subprocess.run", return_value=mock_result) as run:
        result = detect_gpu()

    assert result.available is True
    assert result.name == "NVIDIA GeForce RTX 5060 Ti"
    assert gpu_preferred(result) is True
    assert "preferred" in (result.note or "").lower()
    run.assert_called_once()
    args = run.call_args[0][0]
    assert args[0] == "nvidia-smi"
    assert "--query-gpu=name" in args


def test_gpu_preferred_ignores_device_name_string():
    """Gates must use available only — never SKU / name forks (Decision #003 #9)."""
    assert gpu_preferred(GpuCapability(available=True, name="Any Vendor GPU")) is True
    assert gpu_preferred(GpuCapability(available=True, name="RTX 5060 Ti")) is True
    assert gpu_preferred(GpuCapability(available=False, name="RTX 5060 Ti")) is False
    assert gpu_preferred(GpuCapability(available=None, name="RTX 5060 Ti")) is False


def test_gpu_unavailable_on_nonzero_exit():
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""

    with patch("capabilities.gpu.subprocess.run", return_value=mock_result):
        result = detect_gpu()

    assert result.available is False
    assert result.name is None
    assert gpu_preferred(result) is False


def test_gpu_unavailable_on_empty_stdout():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "\n  \n"

    with patch("capabilities.gpu.subprocess.run", return_value=mock_result):
        result = detect_gpu()

    assert result.available is False
    assert result.name is None
    assert gpu_preferred(result) is False


def test_gpu_unknown_when_nvidia_smi_missing():
    with patch(
        "capabilities.gpu.subprocess.run",
        side_effect=FileNotFoundError("nvidia-smi"),
    ):
        result = detect_gpu()

    assert result.available is None
    assert result.name is None
    assert gpu_preferred(result) is False
    assert "NVIDIA-first" in (result.note or "")


def test_gpu_unknown_on_timeout():
    with patch(
        "capabilities.gpu.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="nvidia-smi", timeout=1.5),
    ):
        result = detect_gpu()

    assert result.available is None
    assert result.name is None
    assert gpu_preferred(result) is False
