import json
import os
from collections.abc import Iterator

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from core.config import config
from providers.base import AIProvider


class GeminiProvider(AIProvider):
    """
    Gemini implementation of the AIProvider interface.
    """

    def __init__(self) -> None:
        """
        Initialize the Gemini AI client.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables or .env")

        self.client = genai.Client(api_key=api_key)
        self.model = config.get("ai", "model")
        self.history: list[dict] = []
        self.system_prompt: str | None = None

    def set_system_prompt(self, prompt: str) -> None:
        """
        Set the system instruction/prompt for the provider.
        """
        self.system_prompt = prompt

    def clear_history(self) -> None:
        """
        Clear the chat history/context.
        """
        self.history.clear()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2)
    )
    def chat(
        self,
        prompt: str,
        *,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> str | dict:
        """
        Send a chat prompt to the Gemini AI provider.
        """
        self.history.append(
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        )

        config_obj = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=self.system_prompt,
            response_mime_type="application/json" if json_mode else "text/plain"
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=self.history,
            config=config_obj,
        )

        text = response.text or ""
        self.history.append(
            {
                "role": "model",
                "parts": [{"text": text}]
            }
        )

        if json_mode:
            return json.loads(text)

        return text

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2)
    )
    def stream(
        self,
        prompt: str,
        *,
        temperature: float = 0.2,
    ) -> Iterator[str]:
        """
        Send a chat prompt and stream response chunks.
        """
        self.history.append(
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        )

        config_obj = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=self.system_prompt,
            response_mime_type="text/plain"
        )

        response = self.client.models.generate_content_stream(
            model=self.model,
            contents=self.history,
            config=config_obj,
        )

        full_response = ""
        for chunk in response:
            if chunk.text:
                full_response += chunk.text
                yield chunk.text

        self.history.append(
            {
                "role": "model",
                "parts": [{"text": full_response}]
            }
        )
