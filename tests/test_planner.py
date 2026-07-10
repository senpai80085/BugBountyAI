import concurrent.futures
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from core.registry import ToolRegistry
from engine.planner import Planner
from engine.workflow import WorkflowEngine
from models.context import ScanContext
from models.objective import Objective, PlanningMode
from models.plan import PlanResult
from models.ai import PlanDecision
from models.tool import ToolMetadata, ToolResult
from tools.base import Tool


# Mock tools for registry mock setup
class MockToolRecon(Tool):
    metadata = ToolMetadata(
        name="subfinder",
        version="1.0.0",
        author="test",
        description="test",
    )
    def validate(self, **kwargs): pass
    def build(self, **kwargs): return MagicMock()
    def parse(self, stdout: str) -> dict: return {}


@pytest.fixture
def mock_registry():
    r = ToolRegistry()
    r.tools["subfinder"] = MockToolRecon
    return r


@pytest.fixture
def mock_workflow_engine():
    engine = MagicMock(spec=WorkflowEngine)
    engine.workflows_dir = Path("workflows")
    # Mock loaded workflow
    mock_wf = MagicMock()
    mock_wf.name = "recon"
    
    mock_step = MagicMock()
    mock_step.tool = "subfinder"
    mock_step.parallel = False
    
    mock_wf.steps = [mock_step]
    engine.load.return_value = mock_wf
    
    # Mock workflow run returning list of ToolResults
    mock_res = ToolResult(
        command=MagicMock(),
        success=True,
        exit_code=0,
        stdout="done",
        stderr="",
        duration=0.1,
        metadata={}
    )
    engine.run.return_value = [mock_res]
    return engine


def test_manual_mode_success(mock_registry, mock_workflow_engine):
    """Verify manual mode selection behaves correctly."""
    planner = Planner(registry=mock_registry, workflow_engine=mock_workflow_engine)
    context = ScanContext(target="example.com", workspace="ws", loot_dir="l", report_dir="r")
    obj = Objective(text="Scan target", mode=PlanningMode.MANUAL, suggested_workflow="recon")

    res = planner.run(obj, context)
    assert isinstance(res, PlanResult)
    assert res.success is True
    assert res.plan.selected_workflow == "recon"
    assert res.decisions["mode"] == PlanningMode.MANUAL


def test_manual_mode_missing_workflow(mock_registry, mock_workflow_engine):
    """Verify error returns on manual mode without suggested workflow."""
    planner = Planner(registry=mock_registry, workflow_engine=mock_workflow_engine)
    context = ScanContext(target="example.com", workspace="ws", loot_dir="l", report_dir="r")
    obj = Objective(text="Scan target", mode=PlanningMode.MANUAL, suggested_workflow=None)

    res = planner.run(obj, context)
    assert res.success is False
    assert "Manual mode requires suggested_workflow" in res.summary


def test_hybrid_mode_accept_suggestion(mock_registry, mock_workflow_engine):
    """Verify hybrid mode validates user-suggested workflows."""
    with patch("pathlib.Path.exists", return_value=True):
        planner = Planner(registry=mock_registry, workflow_engine=mock_workflow_engine)
        context = ScanContext(target="example.com", workspace="ws", loot_dir="l", report_dir="r")
        obj = Objective(text="Scan target", mode=PlanningMode.HYBRID, suggested_workflow="custom_wf")

        res = planner.run(obj, context)
        assert res.plan.selected_workflow == "custom_wf"


def test_hybrid_mode_fallback_on_missing_suggestion(mock_registry, mock_workflow_engine):
    """Verify hybrid mode falls back to rule-based selection on missing file."""
    with patch("pathlib.Path.exists", return_value=False):
        planner = Planner(registry=mock_registry, workflow_engine=mock_workflow_engine)
        context = ScanContext(target="example.com", workspace="ws", loot_dir="l", report_dir="r")
        obj = Objective(text="Scan target", mode=PlanningMode.HYBRID, suggested_workflow="missing_wf")

        res = planner.run(obj, context)
        assert res.plan.selected_workflow == "recon"


def test_auto_mode_rule_based_matching(mock_registry, mock_workflow_engine):
    """Verify rule-based matching finds appropriate keywords."""
    planner = Planner(registry=mock_registry, workflow_engine=mock_workflow_engine)
    context = ScanContext(target="example.com", workspace="ws", loot_dir="l", report_dir="r")
    obj = Objective(text="run dns subdomains check", mode=PlanningMode.AUTO)

    res = planner.run(obj, context)
    assert res.plan.selected_workflow == "recon"
    assert "Matched recon keywords" in res.plan.reasoning


def test_auto_mode_ai_recommendation(mock_registry, mock_workflow_engine):
    """Verify AI planner suggests workflows correctly when enabled."""
    mock_provider = MagicMock()
    mock_provider.structured.return_value = PlanDecision(
        selected_workflow="recon",
        execution_strategy="parallel",
        reasoning="AI matched target scan requirements",
        expected_outputs=["subdomains.txt"],
        confidence=0.95,
        estimated_duration=120.0
    )
    
    with patch("pathlib.Path.exists", return_value=True):
        planner = Planner(registry=mock_registry, workflow_engine=mock_workflow_engine, provider=mock_provider)
        context = ScanContext(target="example.com", workspace="ws", loot_dir="l", report_dir="r")
        obj = Objective(text="Perform target evaluation", mode=PlanningMode.AUTO)

        res = planner.run(obj, context)
        assert res.success is True
        assert res.plan.selected_workflow == "recon"
        assert res.plan.reasoning == "AI matched target scan requirements"
        assert res.decisions["ai_used"] is True


def test_auto_mode_ai_fails_fallback(mock_registry, mock_workflow_engine):
    """Verify fallback selection is used if AI provider fails."""
    mock_provider = MagicMock()
    mock_provider.structured.side_effect = Exception("API error")
    
    planner = Planner(registry=mock_registry, workflow_engine=mock_workflow_engine, provider=mock_provider)
    context = ScanContext(target="example.com", workspace="ws", loot_dir="l", report_dir="r")
    obj = Objective(text="Perform subdomain lookup", mode=PlanningMode.AUTO)

    res = planner.run(obj, context)
    assert res.success is True
    assert res.plan.selected_workflow == "recon"
    assert "Matched recon keywords" in res.plan.reasoning


def test_planner_missing_capability_error(mock_registry, mock_workflow_engine):
    """Verify that workflow tool capabilities missing from registry are handled safely."""
    mock_wf = MagicMock()
    mock_wf.name = "recon"
    mock_step = MagicMock()
    mock_step.tool = "non_existent_tool"
    mock_wf.steps = [mock_step]
    mock_workflow_engine.load.return_value = mock_wf

    planner = Planner(registry=mock_registry, workflow_engine=mock_workflow_engine)
    context = ScanContext(target="example.com", workspace="ws", loot_dir="l", report_dir="r")
    obj = Objective(text="Scan target", mode=PlanningMode.AUTO)

    res = planner.run(obj, context)
    assert res.success is False
    assert "Required tool capability" in res.summary


def test_planner_telemetry(mock_registry, mock_workflow_engine):
    """Verify planning and execution durations are recorded in telemetry."""
    planner = Planner(registry=mock_registry, workflow_engine=mock_workflow_engine)
    context = ScanContext(target="example.com", workspace="ws", loot_dir="l", report_dir="r")
    obj = Objective(text="Scan target", mode=PlanningMode.AUTO)

    res = planner.run(obj, context)
    assert res.planning_duration >= 0.0
    assert res.actual_duration >= 0.0
    assert res.tool_count == 1
    assert res.plan.estimated_duration == 10.0


def test_simultaneous_planners(mock_registry, mock_workflow_engine):
    """Verify concurrent planner operations can run simultaneously."""
    planner = Planner(registry=mock_registry, workflow_engine=mock_workflow_engine)
    
    contexts = [
        ScanContext(target=f"target_{i}.com", workspace="ws", loot_dir="l", report_dir="r")
        for i in range(5)
    ]
    objectives = [
        Objective(text=f"Scan target_{i}", mode=PlanningMode.AUTO)
        for i in range(5)
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = [
            pool.submit(planner.run, obj, ctx)
            for obj, ctx in zip(objectives, contexts)
        ]
        results = [f.result() for f in futures]

    for res in results:
        assert res.success is True
        assert res.plan.selected_workflow == "recon"
