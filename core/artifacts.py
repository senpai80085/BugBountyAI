from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import uuid

from core.command import Command
from core.executor import Executor
from core.logger import logger
from models.artifact import Artifact


class ArtifactManager:
    """
    Single source of truth for scan artifact paths, workspace setup, file downloads,
    and remote workspace cleanups. Uses Executor exclusively to perform host tasks.
    """

    def __init__(self, executor: Executor, scan_id: str) -> None:
        self.executor = executor
        self.scan_id = scan_id
        self.remote_workspace = f"/tmp/bugbounty/{scan_id}"
        self.artifacts: dict[str, Artifact] = {}

    def create_workspace(self) -> None:
        """
        Create the unique remote workspace directories via the Executor.
        """
        logger.info(f"[{self.scan_id}] Creating remote workspace directories under: {self.remote_workspace}")
        # Run mkdir -p for the main workspace and artifacts subdirectory
        cmd = Command(executable="mkdir", args=["-p", f"{self.remote_workspace}/artifacts"])
        self.executor.run(cmd)

    def register_artifact(self, artifact_type: str, filename: str, remote_path: str) -> Artifact:
        """
        Register a remote file artifact, dynamically calculating size and checksum via Executor.
        """
        artifact_id = str(uuid.uuid4())
        
        # Calculate remote file size using wc -c or stat
        size = 0
        size_cmd = Command(executable="stat", args=["-c", "%s", remote_path])
        res_size = self.executor.run(size_cmd)
        if res_size.exit_code == 0:
            try:
                size = int(res_size.stdout.strip())
            except ValueError:
                pass

        # Calculate SHA256 checksum remotely
        checksum = ""
        chk_cmd = Command(executable="sha256sum", args=[remote_path])
        res_chk = self.executor.run(chk_cmd)
        if res_chk.exit_code == 0:
            parts = res_chk.stdout.split()
            if parts:
                checksum = parts[0].strip()

        artifact = Artifact(
            id=artifact_id,
            type=artifact_type,
            filename=filename,
            remote_path=remote_path,
            local_path="",
            checksum=checksum,
            size=size,
            created_at=datetime.utcnow(),
        )
        self.artifacts[artifact_id] = artifact
        logger.info(f"[{self.scan_id}] Registered remote artifact: {filename} ({artifact_type}, {size} bytes)")
        return artifact

    def download_artifact(self, artifact_id: str, local_dir: str) -> Artifact:
        """
        Download the registered artifact to the local host and update its local_path.
        """
        artifact = self.artifacts.get(artifact_id)
        if not artifact:
            raise KeyError(f"No artifact registered with ID: {artifact_id}")

        os.makedirs(local_dir, exist_ok=True)
        local_path = str(Path(local_dir) / artifact.filename)
        
        logger.info(f"[{self.scan_id}] Downloading remote artifact {artifact.remote_path} -> {local_path}")
        self.executor.download(artifact.remote_path, local_path)

        # Update artifact local path using replace
        from dataclasses import replace
        updated = replace(artifact, local_path=local_path)
        self.artifacts[artifact_id] = updated
        return updated

    def cleanup(self) -> None:
        """
        Remove the unique remote scan workspace directory.
        """
        logger.info(f"[{self.scan_id}] Cleaning remote workspace: {self.remote_workspace}")
        cmd = Command(executable="rm", args=["-rf", self.remote_workspace])
        self.executor.run(cmd)

    def export(self) -> list[Artifact]:
        """
        Retrieve all registered artifacts sorted by creation timestamp.
        """
        return list(self.artifacts.values())
