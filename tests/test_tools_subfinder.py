import pytest
from unittest.mock import MagicMock
from core.backend import ExecutionResult
from core.command import Command
from models.tool import ToolResult
from tools.subfinder import SubfinderTool


def test_subfinder_validation():
    """Verify that Subfinder validates correct parameters."""
    tool = SubfinderTool()
    # Should fail if 'domain' is missing
    with pytest.raises(ValueError, match="Parameter 'domain' is required"):
        tool.validate()

    # Should fail if 'domain' is not a non-empty string
    with pytest.raises(ValueError, match="must be a non-empty string"):
        tool.validate(domain="")


def test_subfinder_build():
    """Verify that Subfinder Command is built correctly."""
    tool = SubfinderTool()
    cmd = tool.build(domain="example.com")
    assert isinstance(cmd, Command)
    assert cmd.executable == "subfinder"
    assert cmd.args == ["-d", "example.com", "-silent"]


def test_subfinder_execution():
    """Verify that Subfinder Tool executes returning ToolResult."""
    tool = SubfinderTool()

    mock_executor = MagicMock()
    mock_executor.run.return_value = ExecutionResult(
        command="subfinder -d example.com -o -",
        stdout="sub1.example.com\nsub2.example.com\n",
        stderr="",
        exit_code=0,
    )

    res = tool.execute(mock_executor, domain="example.com")
    assert isinstance(res, ToolResult)
    assert res.command.executable == "subfinder"
    assert res.success is True
    assert res.exit_code == 0
    assert res.stdout == "sub1.example.com\nsub2.example.com\n"
    assert res.metadata == {"subdomains": ["sub1.example.com", "sub2.example.com"]}


def test_subfinder_parse():
    """Verify that parse correctly structures subdomains from stdout."""
    tool = SubfinderTool()
    parsed = tool.parse("sub1.example.com\n\nsub2.example.com")
    assert parsed == {"subdomains": ["sub1.example.com", "sub2.example.com"]}
