from collections.abc import Iterator
import pytest
from providers.base import AIProvider


def test_cannot_instantiate_base_provider():
    """Verify that AIProvider itself cannot be instantiated directly."""
    with pytest.raises(TypeError):
        AIProvider()  # type: ignore[abstract]


def test_concrete_subclass_instantiation():
    """Verify that a subclass implementing all methods can be instantiated."""

    class ConcreteProvider(AIProvider):
        def set_system_prompt(self, prompt: str) -> None:
            pass

        def clear_history(self) -> None:
            pass

        def chat(
            self,
            prompt: str,
            *,
            temperature: float = 0.2,
            json_mode: bool = False,
        ) -> str | dict:
            return "response"

        def stream(
            self,
            prompt: str,
            *,
            temperature: float = 0.2,
        ) -> Iterator[str]:
            yield "response"

    provider = ConcreteProvider()
    assert isinstance(provider, AIProvider)
    assert provider.chat("test") == "response"
    assert list(provider.stream("test")) == ["response"]


def test_missing_methods_raise_type_error():
    """Verify that omitting abstract methods prevents instantiation."""

    class IncompleteProvider(AIProvider):
        def set_system_prompt(self, prompt: str) -> None:
            pass

    with pytest.raises(TypeError):
        IncompleteProvider()  # type: ignore[abstract]

