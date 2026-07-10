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
    assert cmd.args == ["-o", "-", "-u", "example.com"]


def test_nuclei_parse():
    """Verify that NucleiTool parses nuclei standard findings lines."""
    tool = NucleiTool()
    parsed = tool.parse(
        "[git-core-config] [http] [medium] http://example.com/.git/config\n"
        "[tech-detect] [http] [info] http://example.com\n"
    )
    vulns = parsed["vulnerabilities"]
    assert len(vulns) == 2
    assert vulns[0] == {
        "template_id": "git-core-config",
        "protocol": "http",
        "severity": "medium",
        "url": "http://example.com/.git/config"
    }
    assert vulns[1] == {
        "template_id": "tech-detect",
        "protocol": "http",
        "severity": "info",
        "url": "http://example.com"
    }
