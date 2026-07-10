import os
import threading
from pathlib import Path

import paramiko

from core.config import config
from core.logger import logger


class SSHClient:

    def __init__(self):

        self.host = config.get("ssh", "host")
        self.port = config.get("ssh", "port")
        self.username = config.get("ssh", "username")
        self.key = Path(config.get("ssh", "private_key")).expanduser()
        self.timeout = config.get("ssh", "timeout")

        self.client = None
        self.sftp = None
        self.lock = threading.Lock()

    def connect(self):

        if self.client:
            return

        logger.info(f"Connecting to {self.host}")

        self.client = paramiko.SSHClient()

        self.client.set_missing_host_key_policy(
            paramiko.AutoAddPolicy()
        )

        self.client.connect(
            hostname=self.host,
            port=self.port,
            username=self.username,
            key_filename=str(self.key),
            timeout=self.timeout,
        )

        self.sftp = self.client.open_sftp()

        logger.info("SSH connected")

    def disconnect(self):

        if self.sftp:
            self.sftp.close()

        if self.client:
            self.client.close()

        self.client = None
        self.sftp = None

        logger.info("SSH disconnected")

    def execute(self, command: str):

        with self.lock:

            self.connect()

            logger.info(command)

            stdin, stdout, stderr = self.client.exec_command(
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

    def upload(self, local_file, remote_file):
        with self.lock:
            self.connect()
            self.sftp.put(local_file, remote_file)

    def download(self, remote_file, local_file):
        with self.lock:
            self.connect()
            self.sftp.get(remote_file, local_file)

    def exists(self, remote_path):
        with self.lock:
            self.connect()
            try:
                self.sftp.stat(remote_path)
                return True
            except FileNotFoundError:
                return False

    def mkdir(self, remote_dir):
        with self.lock:
            self.connect()
            try:
                self.sftp.mkdir(remote_dir)
            except IOError:
                pass

    def __enter__(self):

        self.connect()

        return self

    def __exit__(self, exc_type, exc, tb):

        self.disconnect()
