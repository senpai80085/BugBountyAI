import time
from unittest.mock import MagicMock
from core.backend import ExecutionResult
from core.command import Command
from core.executor import Executor
from core.registry import ToolRegistry
from engine.workflow import WorkflowEngine
from models.context import ScanContext
from models.tool import ToolMetadata
from models.workflow import Workflow, WorkflowStep
from tools.base import Tool



def test_benchmark_100_tools_scaling():
    """Benchmark executing a workflow containing 100 sequential mock tool steps."""
    registry = ToolRegistry()
    mock_backend = MagicMock()
    mock_backend.run.return_value = ExecutionResult(
        command="benchmark",
        stdout="bench_out",
        stderr="",
        exit_code=0
    )
    executor = Executor(backend=mock_backend)

    # 1. Register 100 mock tools dynamically in the registry
    for i in range(1, 101):
        tool_name = f"bench_tool_{i}"
        
        # Build mock Tool dynamically
        class DynamicallyCreatedTool(Tool):
            metadata = ToolMetadata(
                name=tool_name,
                version="1.0.0",
                author="bench",
                description="bench",
            )
            def validate(self, **kwargs): pass
            def build(self, **kwargs): return Command(executable=tool_name)
            def parse(self, stdout: str) -> dict:
                return {f"out_{tool_name}": "data"}

        registry.tools[tool_name] = DynamicallyCreatedTool

    engine = WorkflowEngine(registry=registry, executor=executor)

    # 2. Build a workflow with 100 sequential steps (each depending on the previous one)
    steps = []
    # Step 1
    steps.append(WorkflowStep(tool="bench_tool_1"))
    # Steps 2 to 100
    for i in range(2, 101):
        steps.append(
            WorkflowStep(
                tool=f"bench_tool_{i}",
                depends_on=[f"bench_tool_{i-1}"]
            )
        )

    workflow = Workflow(name="benchmark_100", steps=steps)

    context = ScanContext(
        target="bench.com",
        workspace="ws",
        loot_dir="loot",
        report_dir="reports"
    )

    # 3. Time the execution
    start_time = time.perf_counter()
    results = engine.run(workflow, context)
    total_duration = time.perf_counter() - start_time

    # 4. Assertions
    assert len(results) == 100
    assert results[99].command.executable == "bench_tool_100"
    assert context.get_result("bench_tool_100").success is True
    # Benchmark target: 100 mock tools must process in less than 2.0 seconds
    assert total_duration < 2.0
