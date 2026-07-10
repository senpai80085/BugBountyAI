import pytest
from unittest.mock import MagicMock
from core.backend import ExecutionResult
from core.command import Command
from models.tool import ToolMetadata, ToolResult
from tools.base import Tool


def test_tool_cannot_instantiate_base():
    """Verify that Tool base class cannot be instantiated or run directly due to abstract methods."""
    with pytest.raises(TypeError):
        Tool()  # type: ignore[abstract]


def test_tool_execution_flow():
    """Verify that concrete tool validates, builds, executes and parses correctly returning ToolResult."""

    class ConcreteTool(Tool):
        metadata = ToolMetadata(
            name="test_tool",
            version="1.0.0",
            author="test_author",
            description="test_desc",
            tags=["test"],
            category="test",
            requirements=[],
            supports_parallel=False,
        )

        def validate(self, **kwargs):
            if "fail" in kwargs:
                raise ValueError("Validation failed")

        def build(self, **kwargs) -> Command:
            return Command(executable="echo", args=[kwargs.get("msg", "hello")])

        def parse(self, stdout: str) -> dict:
            return {"echo_msg": stdout.strip()}

    tool = ConcreteTool()
    assert tool.metadata.name == "test_tool"

    # Mock executor
    mock_executor = MagicMock()
    mock_executor.run.return_value = ExecutionResult(
        command="echo hello",
        stdout="hello\n",
        stderr="",
        exit_code=0,
    )

    # Test success flow
    res = tool.execute(mock_executor, msg="hello")
    assert isinstance(res, ToolResult)
    assert res.command.executable == "echo"
    assert res.success is True
    assert res.exit_code == 0
    assert res.stdout == "hello\n"
    assert res.duration >= 0.0
    assert res.metadata == {"echo_msg": "hello"}

    # Test validation fail
    with pytest.raises(ValueError, match="Validation failed"):
        tool.execute(mock_executor, fail=True)