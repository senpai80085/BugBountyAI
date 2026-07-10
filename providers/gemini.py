from __future__ import annotations

import os
import time
from collections.abc import Iterator
from typing import Any, Optional, Type, TYPE_CHECKING

from google import genai
from google.genai import types
from google.genai.errors import APIError
from tenacity import retry, stop_after_attempt, wait_exponential

from core.config import config
from providers.base import (
    AIProvider,
    AIProviderError,
    AuthenticationError,
    ContextOverflowError,
    ProviderUnavailableError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)
from providers.capabilities import ProviderCapabilities

from memory.conversation import Role

if TYPE_CHECKING:
    from memory.conversation import Conversation
    from pydantic import BaseModel


def map_exception(e: Exception) -> Exception:
    """
    Map downstream SDK exceptions to unified AIProviderError exceptions.
    """
    if isinstance(e, AIProviderError):
        return e

    err_msg = str(e).lower()
    if isinstance(e, APIError):
        code = e.code
        # Code-first matching to prevent cross-talk on keywords like "limit"
        if code in [401, 403]:
            return AuthenticationError(f"AI Authentication failed (code={code}): {e}")
        if code == 429:
            return RateLimitError(f"AI Rate limit exceeded (code={code}): {e}")
        if code == 408:
            return TimeoutError(f"AI Request timed out (code={code}): {e}")
        if code == 400 and ("context" in err_msg or "token" in err_msg or "limit" in err_msg):
            return ContextOverflowError(f"AI Context boundary exceeded (code={code}): {e}")
        if code >= 500:
            return ProviderUnavailableError(f"AI Provider unavailable (code={code}): {e}")

        # Substring keyword matching as fallbacks
        if "auth" in err_msg or "api key" in err_msg or "unauthorized" in err_msg:
            return AuthenticationError(f"AI Authentication failed (code={code}): {e}")
        if "rate" in err_msg or "quota" in err_msg:
            return RateLimitError(f"AI Rate limit exceeded (code={code}): {e}")
        if "timeout" in err_msg or "deadline" in err_msg:
            return TimeoutError(f"AI Request timed out (code={code}): {e}")
        if "unavailable" in err_msg:
            return ProviderUnavailableError(f"AI Provider unavailable (code={code}): {e}")

    if "timeout" in err_msg or "deadline" in err_msg:
        return TimeoutError(f"AI Request timed out: {e}")
    if "connection" in err_msg or "unreachable" in err_msg or "dns" in err_msg:
        return ProviderUnavailableError(f"AI Provider unreachable: {e}")

    return AIProviderError(f"AI Provider error: {e}")


class GeminiProvider(AIProvider):
    """
    Gemini reference implementation of the AIProvider interface.
    Generic LLM wrapper decoupled from bug bounty context.
    """

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise AuthenticationError("GEMINI_API_KEY not found in environment variables.")

        try:
            self.client = genai.Client(api_key=api_key)
        except Exception as e:
            raise AuthenticationError(f"Failed to initialize Gemini Client: {e}")

        # Provider configurations
        self.model_name = config.get("ai", "model")
        
        # Define provider capabilities
        self._capabilities = ProviderCapabilities(
            provider_name="Gemini",
            provider_version="2.0",
            supported_features=["chat", "stream", "structured", "embedding"],
            context_window=32768,
            max_output_tokens=8192,
            supports_embedding=True,
            supports_streaming=True,
            supports_structured=True,
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def health(self) -> bool:
        """
        Validate provider health by executing a minor token count request.
        """
        try:
            self.count_tokens("health check")
            return True
        except Exception:
            return False

    def _prepare_contents(self, conversation: Conversation) -> tuple[list[dict[str, Any]], Optional[str]]:
        """
        Map memory.Conversation messages sequence to Google GenAI content parts,
        and extract the system instructions.
        """
        contents = []
        system_instruction = None
        
        for msg in conversation.get_messages():
            if msg.role.value == "system":
                system_instruction = msg.content
            elif msg.role.value == "user":
                contents.append({"role": "user", "parts": [{"text": msg.content}]})
            elif msg.role.value == "model":
                contents.append({"role": "model", "parts": [{"text": msg.content}]})
                
        return contents, system_instruction

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2),
        reraise=True,
    )
    def chat(self, conversation: Conversation, *, temperature: float = 0.2) -> str:
        """
        Execute chat completion synchronously.
        """
        contents, system_instruction = self._prepare_contents(conversation)
        config_obj = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
            response_mime_type="text/plain",
        )

        start_time = time.perf_counter()
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config_obj,
            )
            _latency = time.perf_counter() - start_time
            text = response.text or ""

            # Update conversation token usage metrics
            p_tok = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
            input_tokens = p_tok if p_tok is not None else 0
            c_tok = response.usage_metadata.candidates_token_count if response.usage_metadata else 0
            output_tokens = c_tok if c_tok is not None else 0
            t_tok = response.usage_metadata.total_token_count if response.usage_metadata else 0
            total_tokens = t_tok if t_tok is not None else 0

            conversation.token_usage.input_tokens += input_tokens
            conversation.token_usage.output_tokens += output_tokens
            conversation.token_usage.total_tokens += total_tokens
            conversation.token_usage.estimated_cost += (input_tokens * 0.000000075 + output_tokens * 0.00000025)

            # Append assistant response back to the shared conversation memory
            conversation.add_message(role=Role.MODEL, content=text)
            return text
        except Exception as e:
            raise map_exception(e)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2),
        reraise=True,
    )
    def stream(self, conversation: Conversation, *, temperature: float = 0.2) -> Iterator[str]:
        """
        Execute chat completion returning stream iterator chunks.
        """
        contents, system_instruction = self._prepare_contents(conversation)
        config_obj = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
            response_mime_type="text/plain",
        )

        try:
            response_stream = self.client.models.generate_content_stream(
                model=self.model_name,
                contents=contents,
                config=config_obj,
            )

            full_text = ""
            for chunk in response_stream:
                if chunk.text:
                    full_text += chunk.text
                    yield chunk.text

            # Update history memory with final merged stream completion outcome
            conversation.add_message(role=Role.MODEL, content=full_text)
        except Exception as e:
            raise map_exception(e)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2),
        reraise=True,
    )
    def structured(
        self,
        conversation: Conversation,
        response_schema: Type[BaseModel],
        *,
        temperature: float = 0.2,
    ) -> Any:
        """
        Execute chat completion requesting JSON output conforming to a Pydantic schema structure.
        """
        contents, system_instruction = self._prepare_contents(conversation)
        config_obj = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_schema,
        )

        start_time = time.perf_counter()
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config_obj,
            )
            _latency = time.perf_counter() - start_time
            text = response.text or ""

            # Update token usage stats
            p_tok = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
            input_tokens = p_tok if p_tok is not None else 0
            c_tok = response.usage_metadata.candidates_token_count if response.usage_metadata else 0
            output_tokens = c_tok if c_tok is not None else 0
            t_tok = response.usage_metadata.total_token_count if response.usage_metadata else 0
            total_tokens = t_tok if t_tok is not None else 0

            conversation.token_usage.input_tokens += input_tokens
            conversation.token_usage.output_tokens += output_tokens
            conversation.token_usage.total_tokens += total_tokens
            conversation.token_usage.estimated_cost += (input_tokens * 0.000000075 + output_tokens * 0.00000025)

            # Validate structural Pydantic mapping
            parsed_data = response_schema.model_validate_json(text)
            
            # Save assistant response message
            conversation.add_message(role=Role.MODEL, content=text)
            return parsed_data
        except Exception as e:
            # Wrap any schema parsing error or API error cleanly
            raise ValidationError(f"Failed structured response Pydantic parsing: {e}")

    def embed(self, text: str) -> list[float]:
        """
        Request embedding vector representation for input content text.
        """
        try:
            response = self.client.models.embed_content(
                model="text-embedding-004",
                contents=text,
            )
            if response.embeddings and response.embeddings[0].values is not None:
                return [float(x) for x in response.embeddings[0].values]
            raise AIProviderError("Embed content returned empty embedding values.")
        except Exception as e:
            raise map_exception(e)

    def count_tokens(self, text: str) -> int:
        """
        Retrieve token count estimation for the provided content string.
        """
        try:
            response = self.client.models.count_tokens(
                model=self.model_name,
                contents=text,
            )
            toks = response.total_tokens
            return toks if toks is not None else 0
        except Exception as e:
            raise map_exception(e)
