from __future__ import annotations

import importlib
import inspect
import pkgutil

from tools.base import Tool


class ToolRegistry:

    def __init__(self):
        self.tools = {}

    def discover(self):

        import tools

        for _, module_name, _ in pkgutil.iter_modules(tools.__path__):

            if module_name == "base":
                continue

            module = importlib.import_module(f"tools.{module_name}")

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Tool) and obj is not Tool:
                    self.tools[obj.metadata.name] = obj


    def get(self, name):

        return self.tools[name]

    def list(self):

        return sorted(self.tools.keys())


registry = ToolRegistry()