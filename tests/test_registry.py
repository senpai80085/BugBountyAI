from core.registry import ToolRegistry, registry
from tools.base import Tool


def test_registry_discover_and_list():
    """Verify that ToolRegistry discovers tools in the tools folder correctly."""
    r = ToolRegistry()
    r.discover()

    tool_names = r.list()
    assert "subfinder" in tool_names

    # Retrieve a tool
    subfinder_cls = r.get("subfinder")
    assert issubclass(subfinder_cls, Tool)
    assert subfinder_cls.metadata.name == "subfinder"


def test_registry_singleton():
    """Verify that the module-level registry singleton behaves as expected."""
    registry.discover()
    assert "subfinder" in registry.list()