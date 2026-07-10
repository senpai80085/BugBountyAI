from unittest.mock import MagicMock
from core.executor import Executor
from core.registry import ToolRegistry
from engine.planner import Planner
from models.context import ScanContext
from models.plan import Plan
from providers.base import AIProvider


def test_planner_interface():
    mock_registry = MagicMock()
    mock_provider = MagicMock()
    mock_executor = MagicMock()

    planner = Planner(registry=mock_registry, provider=mock_provider, executor=mock_executor)

    context = ScanContext(
        target="example.com",
        workspace="workspace",
        loot_dir="loot",
        report_dir="reports",
    )

    plan = planner.run(context)
    assert isinstance(plan, Plan)
    assert plan.objective == "Scan example.com"
