import pytest
from tools.naabu import NaabuTool


def test_naabu_validation():
    """Verify that NaabuTool validates host inputs correctly."""
    tool = NaabuTool()
    with pytest.raises(ValueError, match="Either 'target' or 'input_file'"):
        tool.validate()

    with pytest.raises(ValueError, match="must be a non-empty string"):
        tool.validate(target="")


def test_naabu_build():
    """Verify that NaabuTool builds port scanning command correctly."""
    tool = NaabuTool()
    cmd = tool.build(target="127.0.0.1")
    assert cmd.executable == "naabu"
    assert cmd.args == ["-silent", "-top-ports", "100", "-host", "127.0.0.1"]

    cmd2 = tool.build(input_file="subs.txt")
    assert cmd2.args == ["-silent", "-top-ports", "100", "-list", "subs.txt"]


def test_naabu_parse():
    """Verify that NaabuTool parses open ports correctly."""
    tool = NaabuTool()
    parsed = tool.parse("example.com:80\n127.0.0.1:443\ninvalid_line\n")
    assert parsed == {
        "ports": [
            {"host": "example.com", "port": 80},
            {"host": "127.0.0.1", "port": 443}
        ]
    }
