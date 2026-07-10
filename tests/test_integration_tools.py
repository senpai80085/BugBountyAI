import socket
import pytest

from core.backend import SSHBackend
from core.executor import Executor
from tools.subfinder import SubfinderTool
from tools.httpx import HttpxTool
from tools.katana import KatanaTool
from tools.naabu import NaabuTool
from tools.nuclei import NucleiTool


def is_ssh_reachable() -> bool:
    """Helper to check if the Kali Linux VM port 22 is reachable."""
    try:
        sock = socket.create_connection(("192.168.164.128", 22), timeout=1.0)
        sock.close()
        return True
    except Exception:
        return False


# Skip all tests in this module if the Kali Linux VM is not reachable
pytestmark = pytest.mark.skipif(
    not is_ssh_reachable(),
    reason="Kali Linux SSH VM (192.168.164.128:22) is not reachable. Skipping integration tests."
)


@pytest.fixture
def ssh_executor():
    backend = SSHBackend()
    executor = Executor(backend=backend)
    yield executor
    backend.close()


def test_subfinder_integration(ssh_executor):
    tool = SubfinderTool()
    res = tool.execute(ssh_executor, domain="example.com")
    assert res.success is True
    assert "subdomains" in res.metadata
    assert len(res.metadata["subdomains"]) > 0


def test_httpx_integration(ssh_executor):
    tool = HttpxTool()
    res = tool.execute(ssh_executor, target="https://example.com")
    assert res.success is True
    assert "endpoints" in res.metadata
    assert len(res.metadata["endpoints"]) > 0


def test_katana_integration(ssh_executor):
    tool = KatanaTool()
    res = tool.execute(ssh_executor, target="https://example.com")
    assert res.success is True
    assert "urls" in res.metadata


def test_naabu_integration(ssh_executor):
    tool = NaabuTool()
    res = tool.execute(ssh_executor, target="example.com")
    assert res.success is True
    assert "ports" in res.metadata


def test_nuclei_integration(ssh_executor):
    tool = NucleiTool()
    res = tool.execute(ssh_executor, target="example.com")
    assert res.success is True
    assert "vulnerabilities" in res.metadata
