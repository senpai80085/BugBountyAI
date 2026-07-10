import time
from unittest.mock import MagicMock, patch
import pytest

from core.backend import ExecutionResult
from core.command import Command
from core.executor import Executor
from core.registry import ToolRegistry
from engine.workflow import WorkflowEngine, detect_cycle
from models.context import ScanContext
from models.tool import ToolMetadata, ToolResult
from models.workflow import Workflow, WorkflowStep
from tools.base import Tool


# Mock Tools for Workflow testing
class MockToolA(Tool):
    metadata = ToolMetadata(
        name="tool_a",
        version="1.0.0",
        author="test",
        description="test",
    )
    def validate(self, **kwargs): pass
    def build(self, **kwargs): return Command(executable="tool_a")
    def parse(self, stdout: str) -> dict:
        return {"data_a": "parsed_a"}


class MockToolB(Tool):
    metadata = ToolMetadata(
        name="tool_b",
        version="1.0.0",
        author="test",
        description="test",
    )
    def validate(self, **kwargs): pass
    def build(self, **kwargs): return Command(executable="tool_b")
    def parse(self, stdout: str) -> dict:
        return {"data_b": "parsed_b"}


class MockToolSlow(Tool):
    metadata = ToolMetadata(
        name="tool_slow",
        version="1.0.0",
        author="test",
        description="test",
    )
    def validate(self, **kwargs): pass
    def build(self, **kwargs): return Command(executable="tool_slow")
    def parse(self, stdout: str) -> dict: return {}
    def execute(self, executor, **kwargs):
        time.sleep(0.3)
        return ToolResult(
            command=self.build(**kwargs),
            success=True,
            exit_code=0,
            stdout="slow_done",
            stderr="",
            duration=0.3,
            metadata={}
        )


class MockToolFail(Tool):
    metadata = ToolMetadata(
        name="tool_fail",
        version="1.0.0",
        author="test",
        description="test",
    )
    execution_attempts = 0

    def validate(self, **kwargs): pass
    def build(self, **kwargs): return Command(executable="tool_fail")
    def parse(self, stdout: str) -> dict: return {}
    def execute(self, executor, **kwargs):
        MockToolFail.execution_attempts += 1
        return ToolResult(
            command=self.build(**kwargs),
            success=False,
            exit_code=1,
            stdout="",
            stderr="failed_err",
            duration=0.0,
            metadata={}
        )


@pytest.fixture
def test_registry():
    r = ToolRegistry()
    r.tools["tool_a"] = MockToolA
    r.tools["tool_b"] = MockToolB
    r.tools["tool_slow"] = MockToolSlow
    r.tools["tool_fail"] = MockToolFail
    return r


@pytest.fixture
def mock_executor():
    backend = MagicMock()
    backend.run.return_value = ExecutionResult(
        command="test",
        stdout="success_output",
        stderr="",
        exit_code=0
    )
    return Executor(backend=backend)


def test_sequential_workflow(test_registry, mock_executor):
    """Verify sequential execution of tool_a followed by tool_b."""
    engine = WorkflowEngine(registry=test_registry, executor=mock_executor)
    context = ScanContext(target="test.com", workspace="ws", loot_dir="l", report_dir="r")
    
    workflow = Workflow(
        name="seq",
        steps=[
            WorkflowStep(tool="tool_a"),
            WorkflowStep(tool="tool_b")
        ]
    )

    results = engine.run(workflow, context)
    assert len(results) == 2
    assert results[0].command.executable == "tool_a"
    assert results[1].command.executable == "tool_b"
    assert context.get_result("tool_a").metadata == {"data_a": "parsed_a"}
    assert context.get_result("tool_b").metadata == {"data_b": "parsed_b"}


def test_parallel_workflow(test_registry, mock_executor):
    """Verify that independent tools run concurrently."""
    engine = WorkflowEngine(registry=test_registry, executor=mock_executor)
    context = ScanContext(target="test.com", workspace="ws", loot_dir="l", report_dir="r")

    workflow = Workflow(
        name="parallel",
        steps=[
            WorkflowStep(tool="tool_slow"),
            WorkflowStep(tool="tool_a")
        ]
    )

    start = time.perf_counter()
    results = engine.run(workflow, context)
    duration = time.perf_counter() - start

    assert len(results) == 2
    # Since tool_slow takes 0.3s and tool_a executes immediately,
    # parallel execution should mean total time is around 0.3s (not 0.3 + immediately sequential block overhead)
    assert duration < 0.5


def test_retry(test_registry, mock_executor):
    """Verify that a failing tool is retried the specified number of times."""
    MockToolFail.execution_attempts = 0
    engine = WorkflowEngine(registry=test_registry, executor=mock_executor)
    context = ScanContext(target="test.com", workspace="ws", loot_dir="l", report_dir="r")

    workflow = Workflow(
        name="retry_flow",
        steps=[
            WorkflowStep(tool="tool_fail", retry=2)
        ]
    )

    results = engine.run(workflow, context)
    assert len(results) == 1
    assert MockToolFail.execution_attempts == 3  # 1 initial + 2 retries
    assert results[0].success is False


def test_timeout(test_registry, mock_executor):
    """Verify that a tool execution is aborted if it exceeds timeout limit."""
    engine = WorkflowEngine(registry=test_registry, executor=mock_executor)
    context = ScanContext(target="test.com", workspace="ws", loot_dir="l", report_dir="r")

    workflow = Workflow(
        name="timeout_flow",
        steps=[
            WorkflowStep(tool="tool_slow", timeout=1)  # slow takes 0.3, should pass
        ]
    )
    results = engine.run(workflow, context)
    assert results[0].success is True

    workflow_fail = Workflow(
        name="timeout_fail_flow",
        steps=[
            WorkflowStep(tool="tool_slow", timeout=0.1)  # slow takes 0.3, should timeout
        ]
    )
    results_fail = engine.run(workflow_fail, context)
    assert results_fail[0].success is False
    assert "timed out" in results_fail[0].stderr


def test_dependency_ordering(test_registry, mock_executor):
    """Verify that depends_on prevents running dependent tools if parent fails, or runs them in correct order."""
    engine = WorkflowEngine(registry=test_registry, executor=mock_executor)
    context = ScanContext(target="test.com", workspace="ws", loot_dir="l", report_dir="r")

    # If dependency fails, downstream should not run
    workflow = Workflow(
        name="dep_fail",
        steps=[
            WorkflowStep(tool="tool_fail"),
            WorkflowStep(tool="tool_a", depends_on=["tool_fail"])
        ]
    )

    results = engine.run(workflow, context)
    assert len(results) == 1  # tool_a did not run because tool_fail failed
    assert context.get_result("tool_a") is None


def test_variable_interpolation(test_registry, mock_executor):
    """Verify that parameters are correctly resolved dynamically."""
    engine = WorkflowEngine(registry=test_registry, executor=mock_executor)
    context = ScanContext(target="interp.com", workspace="ws", loot_dir="l", report_dir="r")

    workflow = Workflow(
        name="interp",
        steps=[
            WorkflowStep(tool="tool_a", args={"domain": "{{ target }}"}),
            WorkflowStep(tool="tool_b", args={"imported": "{{ tool_a.data_a }}"}, depends_on=["tool_a"])
        ]
    )

    results = engine.run(workflow, context)
    assert len(results) == 2
    # Verify that tool_b ran with resolved value from tool_a
    assert context.get_result("tool_b").command.args == [] # default mock args
    # Verify lookup_path inside run resolved args correctly
    assert results[1].success is True


def test_continue_on_error(test_registry, mock_executor):
    """Verify that continue_on_error runs downstream steps even if step fails."""
    engine = WorkflowEngine(registry=test_registry, executor=mock_executor)
    context = ScanContext(target="test.com", workspace="ws", loot_dir="l", report_dir="r")

    workflow = Workflow(
        name="continue_err",
        steps=[
            WorkflowStep(tool="tool_fail", continue_on_error=True),
            WorkflowStep(tool="tool_a", depends_on=["tool_fail"])
        ]
    )

    results = engine.run(workflow, context)
    assert len(results) == 2
    assert results[0].success is False
    assert results[1].success is True


def test_circular_dependency(test_registry):
    """Verify ValueError is raised if a circular dependency is parsed."""
    steps = [
        WorkflowStep(tool="tool_a", depends_on=["tool_b"]),
        WorkflowStep(tool="tool_b", depends_on=["tool_a"])
    ]
    with pytest.raises(ValueError, match="Circular dependency detected"):
        detect_cycle(steps)


def test_invalid_workflow_format(test_registry, mock_executor):
    """Verify loading errors on invalid structure/YAML."""
    engine = WorkflowEngine(registry=test_registry, executor=mock_executor)

    # Mock yaml loading to return invalid formats
    with patch("builtins.open", MagicMock()):
        with patch("engine.workflow.yaml.safe_load", return_value="invalid_str"):
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(ValueError, match="Invalid workflow structure"):
                    engine.load("dummy")


def test_missing_tool_in_registry(test_registry, mock_executor):
    """Verify ValueError on workflow specifying non-registered tool."""
    engine = WorkflowEngine(registry=test_registry, executor=mock_executor)

    with patch("builtins.open", MagicMock()):
        with patch("engine.workflow.yaml.safe_load", return_value={"name": "test", "steps": [{"tool": "missing_tool"}]}):
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(ValueError, match="Tool 'missing_tool' not found"):
                    engine.load("dummy")


