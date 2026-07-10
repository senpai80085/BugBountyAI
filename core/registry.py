from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Type

from tools.base import Tool


class ToolRegistry:
    """
    Registry that dynamically discovers, indexes, and loads Tool classes from the tools directory.
    """

    def __init__(self) -> None:
        self.tools: dict[str, Type[Tool]] = {}

    def discover(self) -> None:
        """
        Scan packages in the tools folder and register subclasses inheriting from Tool.
        """
        import tools

        for _, module_name, _ in pkgutil.iter_modules(tools.__path__):
            if module_name == "base":
                continue

            module = importlib.import_module(f"tools.{module_name}")

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Tool) and obj is not Tool:
                    self.tools[obj.metadata.name] = obj

    def get(self, name: str) -> Type[Tool]:
        """
        Retrieve a registered Tool class by its name metadata identifier.
        """
        return self.tools[name]

    def list(self) -> list[str]:
        """
        List all registered tool names sorted lexicographically.
        """
        return sorted(self.tools.keys())


registry = ToolRegistry()