import pytest
from tools.httpx import HttpxTool


def test_httpx_validation():
    """Verify that HttpxTool validates inputs correctly."""
    tool = HttpxTool()
    # Missing args
    with pytest.raises(ValueError, match="Either 'target' or 'input_file'"):
        tool.validate()

    # Invalid string values
    with pytest.raises(ValueError, match="'target' must be a non-empty string"):
        tool.validate(target="")

    with pytest.raises(ValueError, match="'input_file' must be a non-empty string"):
        tool.validate(input_file="")


def test_httpx_build():
    """Verify that HttpxTool builds commands correctly."""
    tool = HttpxTool()
    cmd1 = tool.build(target="https://example.com")
    assert cmd1.executable == "httpx"
    assert cmd1.args == ["-silent", "-json", "-u", "https://example.com"]

    cmd2 = tool.build(input_file="subdomains.txt")
    assert cmd2.args == ["-silent", "-json", "-l", "subdomains.txt"]


def test_httpx_parse():
    """Verify that HttpxTool parses probed endpoints output."""
    tool = HttpxTool()
    parsed = tool.parse(
        '{"url":"https://example.com","status_code":200,"title":"Example Title","tech":["Nginx"]}\n'
        '{"url":"http://unauthorized.com","status_code":403}\n'
        '{"url":"https://broken.com"}\n'
    )
    endpoints = parsed["endpoints"]
    assert len(endpoints) == 3
    assert endpoints[0] == {
        "url": "https://example.com",
        "status_code": 200,
        "title": "Example Title",
        "technologies": ["Nginx"],
        "content_length": 0
    }
    assert endpoints[1] == {
        "url": "http://unauthorized.com",
        "status_code": 403,
        "title": None,
        "technologies": [],
        "content_length": 0
    }
    assert endpoints[2] == {
        "url": "https://broken.com",
        "status_code": None,
        "title": None,
        "technologies": [],
        "content_length": 0
    }
