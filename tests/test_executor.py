from unittest.mock import MagicMock, patch
from core.backend import SSHBackend, LocalBackend, ExecutionResult
from core.command import Command
from core.executor import Executor


def test_command_shell_escape():
    """Verify that Command wraps arguments and performs shell escaping correctly."""
    cmd = Command(executable="subfinder", args=["-d", "example.com", "-silent"])
    assert cmd.shell_escape() == "subfinder -d example.com -silent"

    # Verify escaping of special characters
    cmd_unsafe = Command(executable="echo", args=["hello; rm -rf /"])
    assert cmd_unsafe.shell_escape() == "echo 'hello; rm -rf /'"


def test_ssh_backend_run():
    """Verify that SSHBackend formats Command and delegates to SSHClient."""
    mock_client = MagicMock()
    mock_client.execute.return_value = {
        "command": "whoami",
        "stdout": "kali\n",
        "stderr": "",
        "exit_code": 0,
    }

    backend = SSHBackend(ssh_client=mock_client)
    cmd = Command(executable="whoami")
    res = backend.run(cmd)

    assert isinstance(res, ExecutionResult)
    assert res.exit_code == 0
    assert res.stdout == "kali\n"
    assert res.command == "whoami"
    mock_client.execute.assert_called_once_with("export PATH=$PATH:/home/kali/go/bin; whoami")


def test_ssh_backend_file_operations():
    """Verify that SSHBackend delegates upload and download to SSHClient."""
    mock_client = MagicMock()
    backend = SSHBackend(ssh_client=mock_client)

    backend.upload("local.txt", "remote.txt")
    mock_client.upload.assert_called_once_with("local.txt", "remote.txt")

    backend.download("remote.txt", "local.txt")
    mock_client.download.assert_called_once_with("remote.txt", "local.txt")


def test_local_backend_run():
    """Verify that LocalBackend runs commands locally using subprocess.run."""
    with patch("core.backend.subprocess.run") as mock_sub_run:
        mock_completed_proc = MagicMock()
        mock_completed_proc.stdout = "local_user\n"
        mock_completed_proc.stderr = ""
        mock_completed_proc.returncode = 0
        mock_sub_run.return_value = mock_completed_proc

        backend = LocalBackend()
        cmd = Command(executable="whoami")
        res = backend.run(cmd)

        assert isinstance(res, ExecutionResult)
        assert res.exit_code == 0
        assert res.stdout == "local_user\n"
        mock_sub_run.assert_called_once_with(
            ["whoami"],
            shell=False,
            capture_output=True,
            text=True,
            check=False,
        )


def test_executor_delegation():
    """Verify that Executor delegates operations to the injected ExecutionBackend."""
    mock_backend = MagicMock()
    executor = Executor(backend=mock_backend)

    cmd = Command(executable="whoami")
    executor.run(cmd)
    mock_backend.run.assert_called_once_with(cmd)

    executor.upload("local.txt", "remote.txt")
    mock_backend.upload.assert_called_once_with("local.txt", "remote.txt")

    executor.download("remote.txt", "local.txt")
    mock_backend.download.assert_called_once_with("remote.txt", "local.txt")