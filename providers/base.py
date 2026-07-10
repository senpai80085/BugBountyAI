from abc import ABC, abstractmethod
from collections.abc import Iterator


class AIProvider(ABC):
    """
    Abstract Base Class for all AI providers.
    Every provider plugin MUST inherit from this class.
    """

    @abstractmethod
    def set_system_prompt(self, prompt: str) -> None:
        """
        Set the system instruction/prompt for the provider.
        """
        pass

    @abstractmethod
    def clear_history(self) -> None:
        """
        Clear the chat history/context.
        """
        pass

    @abstractmethod
    def chat(
        self,
        prompt: str,
        *,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> str | dict:
        """
        Send a chat prompt to the AI provider.

        Args:
            prompt: The user prompt.
            temperature: Sampling temperature.
            json_mode: If True, request response as JSON.

        Returns:
            The text response from the provider, or parsed JSON dict.
        """
        pass

    @abstractmethod
    def stream(
        self,
        prompt: str,
        *,
        temperature: float = 0.2,
    ) -> Iterator[str]:
        """
        Send a chat prompt and stream response chunks.

        Args:
            prompt: The user prompt.
            temperature: Sampling temperature.

        Yields:
            Chunks of response text.
        """
        pass

