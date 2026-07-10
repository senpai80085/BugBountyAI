import os
from unittest.mock import MagicMock, patch
import pytest
from providers.gemini import GeminiProvider


@pytest.fixture
def mock_env():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test_api_key"}):
        yield


@pytest.fixture
def mock_genai():
    with patch("providers.gemini.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        yield mock_client


def test_gemini_init_missing_key():
    """Verify initialization failure if GEMINI_API_KEY is not set."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="GEMINI_API_KEY not found"):
            GeminiProvider()


def test_gemini_init_success(mock_env, mock_genai):
    """Verify initialization retrieves config values and instantiates Client."""
    provider = GeminiProvider()
    assert provider.model is not None
    assert provider.history == []
    assert provider.system_prompt is None


def test_set_system_prompt(mock_env, mock_genai):
    """Verify that system prompt can be set correctly."""
    provider = GeminiProvider()
    provider.set_system_prompt("System instruction prompt")
    assert provider.system_prompt == "System instruction prompt"


def test_clear_history(mock_env, mock_genai):
    """Verify that history can be cleared."""
    provider = GeminiProvider()
    provider.history = [{"role": "user", "parts": [{"text": "hello"}]}]
    provider.clear_history()
    assert provider.history == []


def test_chat_text_mode(mock_env, mock_genai):
    """Verify that chat in text mode updates history and returns the text."""
    provider = GeminiProvider()
    provider.set_system_prompt("Test system prompt")

    mock_response = MagicMock()
    mock_response.text = "Hello, user!"
    mock_genai.models.generate_content.return_value = mock_response

    res = provider.chat("Hello model", temperature=0.5)

    assert res == "Hello, user!"
    assert len(provider.history) == 2
    assert provider.history[0]["role"] == "user"
    assert provider.history[0]["parts"][0]["text"] == "Hello model"
    assert provider.history[1]["role"] == "model"
    assert provider.history[1]["parts"][0]["text"] == "Hello, user!"

    # Verify generate_content config argument
    mock_genai.models.generate_content.assert_called_once()
    called_args, called_kwargs = mock_genai.models.generate_content.call_args
    assert called_kwargs["model"] == provider.model
    assert called_kwargs["contents"] == provider.history
    assert called_kwargs["config"].temperature == 0.5
    assert called_kwargs["config"].system_instruction == "Test system prompt"
    assert called_kwargs["config"].response_mime_type == "text/plain"


def test_chat_json_mode(mock_env, mock_genai):
    """Verify that chat in json mode parses response as JSON dict."""
    provider = GeminiProvider()

    mock_response = MagicMock()
    mock_response.text = '{"status": "success", "data": [1, 2, 3]}'
    mock_genai.models.generate_content.return_value = mock_response

    res = provider.chat("Get data", json_mode=True)

    assert isinstance(res, dict)
    assert res["status"] == "success"
    assert res["data"] == [1, 2, 3]

    called_args, called_kwargs = mock_genai.models.generate_content.call_args
    assert called_kwargs["config"].response_mime_type == "application/json"


def test_stream(mock_env, mock_genai):
    """Verify that stream yields chunks and saves full combined response to history."""
    provider = GeminiProvider()

    chunk_1 = MagicMock()
    chunk_1.text = "Part "
    chunk_2 = MagicMock()
    chunk_2.text = "one and part two."
    mock_genai.models.generate_content_stream.return_value = [chunk_1, chunk_2]

    chunks = list(provider.stream("Stream this prompt", temperature=0.7))

    assert chunks == ["Part ", "one and part two."]
    assert len(provider.history) == 2
    assert provider.history[0]["role"] == "user"
    assert provider.history[0]["parts"][0]["text"] == "Stream this prompt"
    assert provider.history[1]["role"] == "model"
    assert provider.history[1]["parts"][0]["text"] == "Part one and part two."

    # Verify config call params
    called_args, called_kwargs = mock_genai.models.generate_content_stream.call_args
    assert called_kwargs["model"] == provider.model
    assert called_kwargs["config"].temperature == 0.7
    assert called_kwargs["config"].response_mime_type == "text/plain"
