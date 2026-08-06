"""Unit tests for Ollama chat client (#70)."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from llm.client import DEFAULT_CHAT_MODEL, ChatClientError, chat, chat_model_available


def test_chat_success():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "message": {"role": "assistant", "content": "  hello from local ai  "},
    }

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.post.return_value = mock_response

    with patch("llm.client.httpx.Client", return_value=mock_client):
        reply = chat("hi", model=DEFAULT_CHAT_MODEL)

    assert reply == "hello from local ai"
    args, kwargs = mock_client.post.call_args
    assert args[0].endswith("/api/chat")
    assert kwargs["json"]["model"] == DEFAULT_CHAT_MODEL
    assert kwargs["json"]["stream"] is False
    assert kwargs["json"]["messages"][-1] == {"role": "user", "content": "hi"}


def test_chat_with_system_message():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "message": {"role": "assistant", "content": "ok"},
    }
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.post.return_value = mock_response

    with patch("llm.client.httpx.Client", return_value=mock_client):
        chat("q", system="You are helpful.")

    payload = mock_client.post.call_args.kwargs["json"]
    assert payload["messages"][0] == {"role": "system", "content": "You are helpful."}


def test_chat_empty_prompt():
    with pytest.raises(ChatClientError, match="non-empty"):
        chat("   ")


def test_chat_connection_error():
    with patch(
        "llm.client.httpx.Client",
        side_effect=httpx.ConnectError("refused"),
    ):
        with pytest.raises(ChatClientError, match="failed"):
            chat("hi")


def test_chat_empty_reply():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"message": {"role": "assistant", "content": "  "}}
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.post.return_value = mock_response

    with patch("llm.client.httpx.Client", return_value=mock_client):
        with pytest.raises(ChatClientError, match="empty"):
            chat("hi")


def test_chat_model_available_delegates():
    with patch("llm.client.model_available", return_value=True) as mock_avail:
        assert chat_model_available("llama3.2:3b") is True
        mock_avail.assert_called_once()
