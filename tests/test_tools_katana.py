import pytest
from tools.katana import KatanaTool


def test_katana_validation():
    """Verify that KatanaTool validates inputs correctly."""
    tool = KatanaTool()
    with pytest.raises(ValueError, match="Parameter 'target' is required"):
        tool.validate()

    with pytest.raises(ValueError, match="must be a non-empty string"):
        tool.validate(target=" ")


def test_katana_build():
    """Verify that KatanaTool builds command correctly."""
    tool = KatanaTool()
    cmd = tool.build(target="https://example.com")
    assert cmd.executable == "katana"
    assert cmd.args == ["-u", "https://example.com", "-o", "-"]


def test_katana_parse():
    """Verify that KatanaTool parses URL list correctly."""
    tool = KatanaTool()
    parsed = tool.parse("http://example.com/about\nhttp://example.com/contact\n")
    assert parsed == {"urls": ["http://example.com/about", "http://example.com/contact"]}
