from collections.abc import Iterator
from typing import Any, Type
import pytest

from providers.base import AIProvider
from providers.capabilities import ProviderCapabilities
from memory.conversation import Conversation
from pydantic import BaseModel


def test_cannot_instantiate_base_provider():
    """Verify that AIProvider itself cannot be instantiated directly."""
    with pytest.raises(TypeError):
        AIProvider()  # type: ignore[abstract]


def test_concrete_subclass_instantiation():
    """Verify that a subclass implementing all methods can be instantiated."""

    class ConcreteProvider(AIProvider):
        @property
        def capabilities(self) -> ProviderCapabilities:
            return ProviderCapabilities(
                provider_name="test",
                provider_version="1.0"
            )

        def health(self) -> bool:
            return True

        def chat(self, conversation: Conversation, *, temperature: float = 0.2) -> str:
            return "response"

        def stream(self, conversation: Conversation, *, temperature: float = 0.2) -> Iterator[str]:
            yield "response"

        def structured(
            self,
            conversation: Conversation,
            response_schema: Type[BaseModel],
            *,
            temperature: float = 0.2,
        ) -> Any:
            return None

        def embed(self, text: str) -> list[float]:
            return [0.1, 0.2]

        def count_tokens(self, text: str) -> int:
            return len(text)

    provider = ConcreteProvider()
    assert isinstance(provider, AIProvider)
    assert provider.chat(Conversation()) == "response"
    assert list(provider.stream(Conversation())) == ["response"]


def test_missing_methods_raise_type_error():
    """Verify that omitting abstract methods prevents instantiation."""

    class IncompleteProvider(AIProvider):
        def health(self) -> bool:
            return True

    with pytest.raises(TypeError):
        IncompleteProvider()  # type: ignore[abstract]
