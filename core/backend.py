from abc import ABC, abstractmethod
from dataclasses import dataclass
import shutil
import subprocess
import threading
from typing import Any

from core.command import Command
from core.ssh import SSHClient, SSHConnectionPool


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

    @abstractmethod
    def exists(self, path: str) -> bool:
        """
        Check if a file/directory exists.
        """
        pass


    def lease_client(self) -> Any:
        """
        No-op context manager for non-pooled backends.
        """
        class DummyLease:
            def __enter__(self) -> Any:
                return None
            def __exit__(self, *args: Any) -> None:
                pass
        return DummyLease()


class SSHBackend(ExecutionBackend):
    """
    Execution backend that runs commands on a remote Kali Linux machine via SSH pool.
    """

    def __init__(self, pool: SSHConnectionPool | None = None, ssh_client: SSHClient | None = None) -> None:
        if pool is not None:
            self.pool = pool
        elif ssh_client is not None:
            self.pool = SSHConnectionPool(size=1, max_size=1)
            self.pool.pool = [ssh_client]
        else:
            self.pool = SSHConnectionPool()
        self.thread_local = threading.local()

    def lease_client(self) -> Any:
        """
        Lease an SSH client for the current thread for the scope of the context.
        """
        class LeaseContext:
            def __init__(self, backend: SSHBackend) -> None:
                self.backend = backend
                self.leased_client: SSHClient | None = None

            def __enter__(self) -> SSHClient:
                self.leased_client = self.backend.pool.acquire()
                self.backend.thread_local.client = self.leased_client
                return self.leased_client

            def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                if self.leased_client:
                    self.backend.pool.release(self.leased_client)
                if hasattr(self.backend.thread_local, "client"):
                    del self.backend.thread_local.client

        return LeaseContext(self)

    def run(self, command: Command) -> ExecutionResult:
        cmd_str = command.shell_escape()
        full_cmd = f"export PATH=$PATH:/home/kali/go/bin; {cmd_str}"

        # Use thread-leased client if present, else lease dynamically
        client = getattr(self.thread_local, "client", None)
        if client is not None:
            res = client.execute(full_cmd)
        else:
            with self.lease_client() as temp_client:
                res = temp_client.execute(full_cmd)

        return ExecutionResult(
            command=cmd_str,
            stdout=res.get("stdout", ""),
            stderr=res.get("stderr", ""),
            exit_code=res.get("exit_code", -1),
        )

    def upload(self, local: str, remote: str) -> None:
        client = getattr(self.thread_local, "client", None)
        if client is not None:
            client.upload(local, remote)
        else:
            with self.lease_client() as temp_client:
                temp_client.upload(local, remote)

    def download(self, remote: str, local: str) -> None:
        client = getattr(self.thread_local, "client", None)
        if client is not None:
            client.download(remote, local)
        else:
            with self.lease_client() as temp_client:
                temp_client.download(remote, local)

    def exists(self, path: str) -> bool:
        client = getattr(self.thread_local, "client", None)
        if client is not None:
            return client.exists(path)
        else:
            with self.lease_client() as temp_client:
                return temp_client.exists(path)

    def close(self) -> None:
        self.pool.close_all()


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

    def exists(self, path: str) -> bool:
        import os
        return os.path.exists(path)
