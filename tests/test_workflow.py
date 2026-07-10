from unittest.mock import MagicMock
import pytest
from core.backend import ExecutionResult
from core.executor import Executor
from core.registry import ToolRegistry
from engine.workflow import WorkflowEngine
from models.context import ScanContext
from models.workflow import Workflow, WorkflowStep
from tools.subfinder import SubfinderTool


def test_workflow_engine_run():
    """Verify that WorkflowEngine correctly executes steps, interpolates variables, and updates context."""
    # Instantiate actual registry and register subfinder
    registry = ToolRegistry()
    registry.tools["subfinder"] = SubfinderTool

    # Mock executor returning ExecutionResult
    mock_backend = MagicMock()
    mock_backend.run.return_value = ExecutionResult(
        command="subfinder -d example.com -o -",
        stdout="sub1.example.com\nsub2.example.com\n",
        stderr="",
        exit_code=0,
    )
    executor = Executor(backend=mock_backend)

    engine = WorkflowEngine(registry=registry, executor=executor)

    # Build ScanContext
    context = ScanContext(
        target="example.com",
        workspace="test_workspace",
        loot_dir="test_loot",
        report_dir="test_report",
    )

    # Setup dummy workflow structure
    workflow = Workflow(
        name="test_recon",
        steps=[
            WorkflowStep(
                tool="subfinder",
                args={"domain": "{{ target }}"}
            )
        ]
    )

    results = engine.run(workflow, context)

    # Assert outcomes
    assert len(results) == 1
    res = results[0]
    assert res.command.executable == "subfinder"
    assert res.success is True
    assert res.metadata == {"subdomains": ["sub1.example.com", "sub2.example.com"]}
    assert context.shared_results["subfinder"] == {"subdomains": ["sub1.example.com", "sub2.example.com"]}
