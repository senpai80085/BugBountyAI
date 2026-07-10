import pytest
from tools.nuclei import NucleiTool


def test_nuclei_validation():
    """Verify that NucleiTool validates targets or input files correctly."""
    tool = NucleiTool()
    with pytest.raises(ValueError, match="Either 'target' or 'input_file'"):
        tool.validate()

    with pytest.raises(ValueError, match="'target' must be a non-empty string"):
        tool.validate(target=" ")


def test_nuclei_build():
    """Verify that NucleiTool builds commands correctly."""
    tool = NucleiTool()
    cmd = tool.build(target="example.com")
    assert cmd.executable == "nuclei"
    assert cmd.args == ["-silent", "-jsonl", "-u", "example.com"]


def test_nuclei_parse():
    """Verify that NucleiTool parses nuclei JSON-lines findings."""
    tool = NucleiTool()
    parsed = tool.parse(
        '{"template-id":"git-core-config","info":{"name":"Git config leak","severity":"medium","description":"Git config exposed"},"matched-at":"http://example.com/.git/config"}\n'
        '{"template-id":"tech-detect","info":{"name":"Technology detection","severity":"info"},"host":"http://example.com"}\n'
    )
    vulns = parsed["vulnerabilities"]
    assert len(vulns) == 2
    assert vulns[0] == {
        "template_id": "git-core-config",
        "name": "Git config leak",
        "severity": "medium",
        "matched_at": "http://example.com/.git/config",
        "description": "Git config exposed"
    }
    assert vulns[1] == {
        "template_id": "tech-detect",
        "name": "Technology detection",
        "severity": "info",
        "matched_at": "http://example.com",
        "description": ""
    }
