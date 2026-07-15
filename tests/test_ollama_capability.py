"""Unit tests for Ollama capability mapping (mocked HTTP / binary checks)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from capabilities.ollama import detect_ollama


@pytest.mark.asyncio
async def test_ollama_available():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"version": "0.5.1"}

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("capabilities.ollama.httpx.AsyncClient", return_value=mock_client):
        result = await detect_ollama()

    assert result.available is True
    assert result.status == "available"
    assert result.version == "0.5.1"


@pytest.mark.asyncio
async def test_ollama_unavailable_when_binary_present():
    with (
        patch(
            "capabilities.ollama.httpx.AsyncClient",
            side_effect=httpx.ConnectError("refused"),
        ),
        patch("capabilities.ollama._ollama_binary_present", return_value=True),
    ):
        result = await detect_ollama()

    assert result.available is False
    assert result.status == "unavailable"
    assert result.version is None


@pytest.mark.asyncio
async def test_ollama_not_installed():
    with (
        patch(
            "capabilities.ollama.httpx.AsyncClient",
            side_effect=httpx.ConnectError("refused"),
        ),
        patch("capabilities.ollama._ollama_binary_present", return_value=False),
    ):
        result = await detect_ollama()

    assert result.available is False
    assert result.status == "not_installed"
    assert result.version is None
