from dataclasses import dataclass
from enum import Enum
import threading
from typing import Callable, Optional


class Role(str, Enum):
    """
    Standard roles in an AI conversation.
    """
    SYSTEM = "system"
    USER = "user"
    MODEL = "model"


@dataclass
class Message:
    """
    Single message in the conversation.
    """
    role: Role
    content: str


@dataclass
class TokenUsage:
    """
    Aggregated token count and tracking values.
    """
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0


class Conversation:
    """
    Thread-safe storage class for managing conversation history and token budgets.
    Allows generic AI providers to receive standard message sequences.
    """

    def __init__(self, max_tokens: int = 8192) -> None:
        self.max_tokens = max_tokens
        self.messages: list[Message] = []
        self.token_usage = TokenUsage()
        self._lock = threading.Lock()

    def add_message(self, role: Role, content: str) -> None:
        """
        Add a message thread-safely.
        """
        with self._lock:
            self.messages.append(Message(role=role, content=content))

    def clear(self) -> None:
        """
        Clear conversation log thread-safely.
        """
        with self._lock:
            self.messages.clear()

    def get_messages(self) -> list[Message]:
        """
        Retrieve messages list clone.
        """
        with self._lock:
            return list(self.messages)

    def trim_history(self, estimate_tokens_fn: Callable[[str], int]) -> None:
        """
        Trim conversation history starting from the oldest non-system message
        until the total estimated token count is within max_tokens limits.
        """
        with self._lock:
            if not self.messages:
                return

            system_msg: Optional[Message] = None
            start_idx = 0
            if self.messages[0].role == Role.SYSTEM:
                system_msg = self.messages[0]
                start_idx = 1

            msgs_to_trim = self.messages[start_idx:]

            def calc_total_tokens() -> int:
                total = 0
                if system_msg:
                    total += estimate_tokens_fn(system_msg.content)
                for msg in msgs_to_trim:
                    total += estimate_tokens_fn(msg.content)
                return total

            while msgs_to_trim and calc_total_tokens() > self.max_tokens:
                msgs_to_trim.pop(0)

            new_messages = []
            if system_msg:
                new_messages.append(system_msg)
            new_messages.extend(msgs_to_trim)
            self.messages = new_messages
