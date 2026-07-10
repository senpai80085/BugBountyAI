from abc import ABC, abstractmethod
from typing import Any

from models.context import ScanContext


class KnowledgeBase(ABC):
    """
    Interface for maintaining extracted asset knowledge, endpoints, and targets across scans.
    """

    @abstractmethod
    def update(self, context: ScanContext, key: str, value: Any) -> None:
        """
        Register or update a fact in the knowledge base.
        """
        pass

    @abstractmethod
    def retrieve(self, context: ScanContext, key: str) -> Any:
        """
        Lookup a registered fact in the knowledge base.
        """
        pass
