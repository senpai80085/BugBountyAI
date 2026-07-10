from abc import ABC, abstractmethod
from typing import Any, Optional


class AICache(ABC):
    """
    Interface representation for future semantic AI caching.
    No active implementation required in Phase 4.
    """

    @abstractmethod
    def get(self, prompt_hash: str) -> Optional[Any]:
        """
        Retrieve cached value by prompt hash identifier.
        """
        pass

    @abstractmethod
    def set(self, prompt_hash: str, value: Any, ttl: int = 3600) -> None:
        """
        Store value under prompt hash key with specified lifetime.
        """
        pass
