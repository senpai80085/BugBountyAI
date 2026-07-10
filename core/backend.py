from abc import ABC, abstractmethod
from dataclasses import dataclass
import shutil
import subprocess

from core.command import Command
from core.ssh import SSHClient


@dataclass(frozen=True)
class ExecutionResult:
    """
    Structured representation of the outcome of a command execution.
    """
    command: str
    stdout: str
    stderr: str
    exit_code: int


class ExecutionBackend(ABC):
    """
    Abstract Base Class for all execution backends.
    """

    @abstractmethod
    def run(self, command: Command) -> ExecutionResult:
        """
        Execute the given command and return the result.
        """
        pass

    @abstractmethod
    def upload(self, local: str, remote: str) -> None:
        """
        Upload a file from local host to execution environment.
        """
        pass

    @abstractmethod
    def download(self, remote: str, local: str) -> None:
        """
        Download a file from execution environment to local host.
        """
        pass


class SSHBackend(ExecutionBackend):
    """
    Execution backend that runs commands on a remote Kali Linux machine via SSH.
    """

    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        self.client = ssh_client or SSHClient()

    def run(self, command: Command) -> ExecutionResult:
        cmd_str = command.shell_escape()
        res = self.client.execute(cmd_str)
        return ExecutionResult(
            command=res.get("command", cmd_str),
            stdout=res.get("stdout", ""),
            stderr=res.get("stderr", ""),
            exit_code=res.get("exit_code", -1),
        )

    def upload(self, local: str, remote: str) -> None:
        self.client.upload(local, remote)

    def download(self, remote: str, local: str) -> None:
        self.client.download(remote, local)

    def close(self) -> None:
        self.client.disconnect()


class LocalBackend(ExecutionBackend):
    """
    Execution backend that runs commands locally on the host machine.
    """

    def run(self, command: Command) -> ExecutionResult:
        cmd_list = [command.executable] + command.args
        cmd_str = " ".join(cmd_list)
        try:
            res = subprocess.run(
                cmd_list,
                shell=False,
                capture_output=True,
                text=True,
                check=False
            )
            return ExecutionResult(
                command=cmd_str,
                stdout=res.stdout,
                stderr=res.stderr,
                exit_code=res.returncode,
            )
        except Exception as e:
            return ExecutionResult(
                command=cmd_str,
                stdout="",
                stderr=str(e),
                exit_code=-1,
            )

    def upload(self, local: str, remote: str) -> None:
        shutil.copy2(local, remote)

    def download(self, remote: str, local: str) -> None:
        shutil.copy2(remote, local)
