from __future__ import annotations

from core.backend import ExecutionBackend, ExecutionResult
from core.command import Command


class Executor:
    """
    Wrapper class that delegates command execution and file transfer tasks
    to an underlying ExecutionBackend.
    """

    def __init__(self, backend: ExecutionBackend) -> None:
        self.backend = backend

    def run(self, command: Command) -> ExecutionResult:
        """
        Execute the given Command using the delegated backend.
        """
        return self.backend.run(command)

    def upload(self, local: str, remote: str) -> None:
        """
        Upload a file using the delegated backend.
        """
        self.backend.upload(local, remote)

    def download(self, remote: str, local: str) -> None:
        """
        Download a file using the delegated backend.
        """
        self.backend.download(remote, local)