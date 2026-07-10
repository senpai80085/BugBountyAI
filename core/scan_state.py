from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from core.command import Command
from core.reporter import to_dict
from models.artifact import Artifact
from models.tool import ToolResult


class ScanState:
    """
    Manages persistent state of scan progress to support resumable scans.
    Saves completed steps and their ToolResults to loot/{scan_id}/state.json.
    """

    def __init__(self, scan_id: str, target: str, workflow: str, workspace: str) -> None:
        self.scan_id = scan_id
        self.target = target
        self.workflow = workflow
        self.workspace = workspace
        self.completed_steps: dict[str, Any] = {}  # tool_name -> ToolResult (serialized dict)

    @classmethod
    def load(cls, scan_id: str, loot_dir: str = "loot") -> ScanState | None:
        state_file = Path(loot_dir) / scan_id / "state.json"
        if not state_file.exists():
            return None
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            state = cls(
                scan_id=data["scan_id"],
                target=data["target"],
                workflow=data["workflow"],
                workspace=data["workspace"],
            )
            state.completed_steps = data.get("completed_steps", {})
            return state
        except Exception:
            return None

    def save(self, loot_dir: str = "loot") -> None:
        state_dir = Path(loot_dir) / self.scan_id
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file = state_dir / "state.json"

        data = {
            "scan_id": self.scan_id,
            "target": self.target,
            "workflow": self.workflow,
            "workspace": self.workspace,
            "completed_steps": self.completed_steps,
        }
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def add_completed_step(self, tool_name: str, result: ToolResult) -> None:
        self.completed_steps[tool_name] = to_dict(result)

    def deserialize_result(self, tool_name: str) -> ToolResult | None:
        data = self.completed_steps.get(tool_name)
        if not data:
            return None

        cmd_data = data.get("command", {})
        command = Command(
            executable=cmd_data.get("executable", ""),
            args=cmd_data.get("args", []),
        )

        artifacts = []
        for a_data in data.get("artifacts", []):
            created_at_val = a_data.get("created_at", "")
            if isinstance(created_at_val, str) and created_at_val:
                try:
                    created_at: Any = datetime.fromisoformat(created_at_val)
                except Exception:
                    created_at = created_at_val
            else:
                created_at = created_at_val

            artifacts.append(
                Artifact(
                    id=a_data.get("id", ""),
                    type=a_data.get("type", ""),
                    filename=a_data.get("filename", ""),
                    remote_path=a_data.get("remote_path", ""),
                    local_path=a_data.get("local_path", ""),
                    checksum=a_data.get("checksum", ""),
                    size=a_data.get("size", 0),
                    created_at=created_at,
                )
            )

        return ToolResult(
            command=command,
            success=data.get("success", False),
            exit_code=data.get("exit_code", 0),
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
            duration=data.get("duration", 0.0),
            artifacts=artifacts,
            metadata=data.get("metadata", {}),
        )

    def verify_artifacts(self, tool_name: str, executor: Any) -> bool:
        """
        Verify that all remote artifacts associated with the completed step actually exist.
        If any are missing, return False (signaling that the step should be rerun).
        """
        data = self.completed_steps.get(tool_name)
        if not data:
            return False

        artifacts_data = data.get("artifacts", [])
        if not artifacts_data:
            # If no artifacts were expected, it's valid
            return True

        for a in artifacts_data:
            remote_path = a.get("remote_path", "")
            if not remote_path:
                return False
            # Verify remote file presence
            try:
                if not executor.exists(remote_path):
                    return False
            except Exception:
                return False

        return True
