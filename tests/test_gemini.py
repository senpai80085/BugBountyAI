import os
from unittest.mock import MagicMock, patch
import pytest
from pydantic import BaseModel

from providers.base import AuthenticationError
from providers.gemini import GeminiProvider
from memory.conversation import Conversation, Role


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
        with pytest.raises(AuthenticationError, match="GEMINI_API_KEY not found"):
            GeminiProvider()


def test_gemini_init_success(mock_env, mock_genai):
    """Verify initialization retrieves config values and maps capabilities."""
    provider = GeminiProvider()
    assert provider.model_name is not None
    assert provider.capabilities.provider_name == "Gemini"
    assert provider.capabilities.supports_structured is True


def test_gemini_health(mock_env, mock_genai):
    """Verify health status returns True if token counting succeeds."""
    provider = GeminiProvider()
    
    # Mock token count response
    mock_res = MagicMock()
    mock_res.total_tokens = 5
    mock_genai.models.count_tokens.return_value = mock_res
    
    assert provider.health() is True


def test_chat_text_mode(mock_env, mock_genai):
    """Verify that chat updates conversation history and returns text response."""
    provider = GeminiProvider()

    mock_response = MagicMock()
    mock_response.text = "Hello, user!"
    mock_response.usage_metadata.prompt_token_count = 10
    mock_response.usage_metadata.candidates_token_count = 5
    mock_response.usage_metadata.total_token_count = 15
    mock_genai.models.generate_content.return_value = mock_response

    conv = Conversation()
    conv.add_message(Role.USER, "Hello model")
    
    res = provider.chat(conv, temperature=0.5)

    assert res == "Hello, user!"
    assert len(conv.get_messages()) == 2
    assert conv.get_messages()[1].role == Role.MODEL
    assert conv.get_messages()[1].content == "Hello, user!"
    assert conv.token_usage.total_tokens == 15


def test_structured_success(mock_env, mock_genai):
    """Verify structured response decodes JSON to Pydantic models."""
    provider = GeminiProvider()

    class Schema(BaseModel):
        status: str
        count: int

    mock_response = MagicMock()
    mock_response.text = '{"status": "success", "count": 42}'
    mock_response.usage_metadata.prompt_token_count = 5
    mock_response.usage_metadata.candidates_token_count = 5
    mock_response.usage_metadata.total_token_count = 10
    mock_genai.models.generate_content.return_value = mock_response

    conv = Conversation()
    conv.add_message(Role.USER, "Get schema")

    res = provider.structured(conv, Schema)
    assert isinstance(res, Schema)
    assert res.status == "success"
    assert res.count == 42


def test_stream_success(mock_env, mock_genai):
    """Verify stream yields chunks and saves full text to conversation."""
    provider = GeminiProvider()

    chunk_1 = MagicMock()
    chunk_1.text = "Part "
    chunk_2 = MagicMock()
    chunk_2.text = "one"
    mock_genai.models.generate_content_stream.return_value = [chunk_1, chunk_2]

    conv = Conversation()
    conv.add_message(Role.USER, "Stream prompt")

    chunks = list(provider.stream(conv))
    assert chunks == ["Part ", "one"]
    assert conv.get_messages()[-1].role == Role.MODEL
    assert conv.get_messages()[-1].content == "Part one"
