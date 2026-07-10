from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Any

import paramiko

from core.config import config
from core.logger import logger


class SSHClient:
    """
    Thread-safe client wrapper for Paramiko SSH and SFTP file operations.
    Centralized execution layer to run commands and manage remote files.
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
        Suppresses OSError from paramiko channel-close race on Windows.
        """
        if self.sftp:
            try:
                self.sftp.close()
            except (OSError, EOFError):
                pass

        if self.client:
            try:
                self.client.close()
            except (OSError, EOFError):
                pass

        self.client = None
        self.sftp = None

        logger.info("SSH disconnected")

    def execute(self, command: str) -> dict[str, Any]:
        """
        Execute command on the remote host and return command outcome.
        Measures duration, sends a heartbeat every 5s, and logs detailed error on failure.
        Protected by self.lock to ensure thread-safe socket usage.
        """
        with self.lock:
            self.connect()
            logger.info(f"Command started: {command}")

            start_time = time.perf_counter()
            assert self.client is not None
            stdin, stdout, stderr = self.client.exec_command(
                command,
                timeout=self.timeout,
            )
            stdin.close()
            channel = stdout.channel

            stdout_chunks: list[str] = []
            stderr_chunks: list[str] = []

            last_heartbeat = start_time

            # Parse clean executable name for the heartbeat (strip shell exports if present)
            cmd_clean = command
            if "export PATH=" in cmd_clean and ";" in cmd_clean:
                cmd_clean = cmd_clean.split(";", 1)[1].strip()
            parts = cmd_clean.split()
            exe_name = parts[0] if parts else "command"
            exe_name = os.path.basename(exe_name)

            while not channel.exit_status_ready():
                # Read stdout
                if channel.recv_ready():
                    data = channel.recv(4096)
                    if data:
                        stdout_chunks.append(data.decode(errors="replace"))

                # Read stderr
                if channel.recv_stderr_ready():
                    data = channel.recv_stderr(4096)
                    if data:
                        stderr_chunks.append(data.decode(errors="replace"))

                # Log heartbeat every 5 seconds
                now = time.perf_counter()
                elapsed = int(now - start_time)
                if now - last_heartbeat >= 5.0:
                    logger.info(f"[RUNNING] {exe_name} ... ({elapsed}s elapsed)")
                    last_heartbeat = now

                time.sleep(0.1)

            # Flush any remaining buffers
            while channel.recv_ready():
                data = channel.recv(4096)
                if data:
                    stdout_chunks.append(data.decode(errors="replace"))

            while channel.recv_stderr_ready():
                data = channel.recv(4096)
                if data:
                    stderr_chunks.append(data.decode(errors="replace"))

            exit_code = channel.recv_exit_status()
            duration = time.perf_counter() - start_time

            logger.info(f"Command finished: {command} in {duration:.2f}s with exit code {exit_code}")

            stdout_str = "".join(stdout_chunks)
            stderr_str = "".join(stderr_chunks)

            # Print detailed block on failure (Step 2 - Most Important)
            if exit_code != 0:
                failure_msg = (
                    f"\nCOMMAND:\n{command}\n\n"
                    f"EXIT CODE:\n{exit_code}\n\n"
                    f"STDERR:\n{stderr_str.strip()}\n\n"
                    f"STDOUT:\n{stdout_str.strip()}"
                )
                logger.error(failure_msg)

            return {
                "command": command,
                "stdout": stdout_str,
                "stderr": stderr_str,
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


class SSHConnectionPool:
    """
    Thread-safe connection pool for managing multiple SSHClient instances.
    """

    def __init__(self, size: int | None = None, max_size: int | None = None) -> None:
        # Resolve pool size configurations
        if size is None:
            try:
                self.size = int(config.get("ssh", "pool_size"))
            except Exception:
                self.size = 2
        else:
            self.size = size

        if max_size is None:
            try:
                self.max_size = int(config.get("ssh", "max_pool_size"))
            except Exception:
                self.max_size = 4
        else:
            self.max_size = max_size

        self.pool: list[SSHClient] = [SSHClient() for _ in range(self.size)]
        self.active_count = self.size
        self._leased: set[SSHClient] = set()
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)

    def acquire(self) -> SSHClient:
        """Acquire an SSHClient. Blocks if none are available and max_size is reached."""
        with self.lock:
            while True:
                # 1. Try to get an inactive client
                for client in self.pool:
                    if client not in self._leased:
                        self._leased.add(client)
                        return client

                # 2. If pool is full of leased clients, try to grow to max_size
                if self.active_count < self.max_size:
                    new_client = SSHClient()
                    self.pool.append(new_client)
                    self.active_count += 1
                    self._leased.add(new_client)
                    return new_client

                # 3. Wait for release
                self.cond.wait()

    def release(self, client: SSHClient) -> None:
        """Release the SSHClient back into the pool."""
        with self.lock:
            if client in self._leased:
                self._leased.remove(client)
            self.cond.notify_all()

    def close_all(self) -> None:
        """Close all connections in the pool."""
        with self.lock:
            for client in self.pool:
                try:
                    client.disconnect()
                except Exception:
                    pass
            self.pool.clear()
            self.active_count = 0
            self.cond.notify_all()
