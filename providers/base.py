from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any, Type, TYPE_CHECKING

from providers.capabilities import ProviderCapabilities

if TYPE_CHECKING:
    from memory.conversation import Conversation
    from pydantic import BaseModel


class AIProviderError(Exception):
    """Base exception for all AI provider operations."""
    pass


class AuthenticationError(AIProviderError):
    """Raised when authentication credentials fail or are invalid."""
    pass


class TimeoutError(AIProviderError):
    """Raised when the AI provider request times out."""
    pass


class RateLimitError(AIProviderError):
    """Raised when rate limits are exceeded."""
    pass


class ValidationError(AIProviderError):
    """Raised when the provider returns a response that fails schema validation."""
    pass


class ContextOverflowError(AIProviderError):
    """Raised when the conversation exceeds context token bounds."""
    pass


class ProviderUnavailableError(AIProviderError):
    """Raised when the provider is unreachable or down."""
    pass


class AIProvider(ABC):
    """
    Abstract Base Class for all AI providers.
    Every provider plugin MUST inherit from this class.
    """

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """
        Return the capabilities profile of this provider.
        """
        pass

    @abstractmethod
    def health(self) -> bool:
        """
        Check provider health status. Returns True if operational, False otherwise.
        """
        pass

    @abstractmethod
    def chat(self, conversation: Conversation, *, temperature: float = 0.2) -> str:
        """
        Send a chat conversation sequence to the provider.
        """
        pass

    @abstractmethod
    def stream(self, conversation: Conversation, *, temperature: float = 0.2) -> Iterator[str]:
        """
        Send a chat conversation prompt and stream response chunks.
        """
        pass

    @abstractmethod
    def structured(
        self,
        conversation: Conversation,
        response_schema: Type[BaseModel],
        *,
        temperature: float = 0.2,
    ) -> Any:
        """
        Send structured requests matching a specific Pydantic schema model.
        """
        pass

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """
        Generate embedding vector list for the text.
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count tokens for the given text.
        """
        pass
