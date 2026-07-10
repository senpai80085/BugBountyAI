from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import paramiko

from core.config import config
from core.logger import logger


class SSHClient:
    """
    Thread-safe client wrapper for Paramiko SSH and SFTP file operations.
    Uses a centralized lock to serialize concurrent command executions and file operations.
    """

    def __init__(self) -> None:
        self.host: str = config.get("ssh", "host")
        self.port: int = config.get("ssh", "port")
        self.username: str = config.get("ssh", "username")
        self.key: Path = Path(config.get("ssh", "private_key")).expanduser()
        self.timeout: float = float(config.get("ssh", "timeout"))

        self.client: paramiko.SSHClient | None = None
        self.sftp: paramiko.SFTPClient | None = None
        self.lock: threading.Lock = threading.Lock()

    def connect(self) -> None:
        """
        Establish SSH connection and SFTP channel if not already connected.
        """
        if self.client:
            return

        logger.info(f"Connecting to {self.host}")

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.client.connect(
            hostname=self.host,
            port=self.port,
            username=self.username,
            key_filename=str(self.key),
            timeout=self.timeout,
        )

        self.sftp = self.client.open_sftp()
        logger.info("SSH connected")

    def disconnect(self) -> None:
        """
        Close active SFTP channel and SSH connection.
        """
        if self.sftp:
            self.sftp.close()

        if self.client:
            self.client.close()

        self.client = None
        self.sftp = None

        logger.info("SSH disconnected")

    def execute(self, command: str) -> dict[str, Any]:
        """
        Execute command on the remote host and return command outcome.
        Protected by self.lock to ensure thread-safe socket usage.
        """
        with self.lock:
            self.connect()
            logger.info(command)

            assert self.client is not None
            _, stdout, stderr = self.client.exec_command(
                command,
                timeout=self.timeout,
            )

            exit_code = stdout.channel.recv_exit_status()

            return {
                "command": command,
                "stdout": stdout.read().decode(),
                "stderr": stderr.read().decode(),
                "exit_code": exit_code,
            }

    def upload(self, local_file: str, remote_file: str) -> None:
        """
        Upload local file to the remote host.
        Protected by self.lock to ensure thread-safe SFTP usage.
        """
        with self.lock:
            self.connect()
            assert self.sftp is not None
            self.sftp.put(local_file, remote_file)

    def download(self, remote_file: str, local_file: str) -> None:
        """
        Download remote file from the host.
        Protected by self.lock to ensure thread-safe SFTP usage.
        """
        with self.lock:
            self.connect()
            assert self.sftp is not None
            self.sftp.get(remote_file, local_file)

    def exists(self, remote_path: str) -> bool:
        """
        Check if remote file path exists on the host.
        Protected by self.lock to ensure thread-safe SFTP usage.
        """
        with self.lock:
            self.connect()
            assert self.sftp is not None
            try:
                self.sftp.stat(remote_path)
                return True
            except FileNotFoundError:
                return False

    def mkdir(self, remote_dir: str) -> None:
        """
        Create remote directory if it does not already exist.
        Protected by self.lock to ensure thread-safe SFTP usage.
        """
        with self.lock:
            self.connect()
            assert self.sftp is not None
            try:
                self.sftp.mkdir(remote_dir)
            except IOError:
                pass

    def __enter__(self) -> SSHClient:
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.disconnect()
