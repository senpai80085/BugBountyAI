import json
from typing import Any

from core.command import Command
from models.tool import ToolMetadata
from tools.base import Tool


class NucleiTool(Tool):
    """
    Tool plugin for nuclei, running vulnerability scans.
    """
    metadata = ToolMetadata(
        name="nuclei",
        version="1.0.0",
        author="BugBountyAI",
        description="Fast and customizable vulnerability scanner based on simple YAML DSL",
        tags=["scan", "vuln"],
        category="scanning",
        requirements=["nuclei"],
        supports_parallel=True,
    )

    def validate(self, **kwargs) -> None:
        """
        Validate that either a target URL/domain/list or an input file path is provided.
        """
        if "target" not in kwargs and "input_file" not in kwargs:
            raise ValueError("Either 'target' or 'input_file' must be provided for nuclei.")

        if "target" in kwargs:
            target = kwargs["target"]
            if not isinstance(target, (str, list)):
                raise ValueError("'target' must be a string or a list of strings.")
            if isinstance(target, str) and not target.strip():
                raise ValueError("'target' must be a non-empty string.")

        if "input_file" in kwargs:
            input_file = kwargs["input_file"]
            if not isinstance(input_file, str) or not input_file.strip():
                raise ValueError("'input_file' must be a non-empty string.")

    def build(self, **kwargs) -> Command:
        """
        Build the nuclei execution Command.
        """
        args = ["-silent", "-jsonl"]
        
        if "target" in kwargs:
            target = kwargs["target"]
            if isinstance(target, list):
                for t in target:
                    args.extend(["-u", str(t)])
            else:
                args.extend(["-u", target])
        elif "input_file" in kwargs:
            args.extend(["-l", kwargs["input_file"]])

        if "output_file" in kwargs:
            args.extend(["-o", kwargs["output_file"]])

        return Command(executable="nuclei", args=args)

    def parse(self, stdout: str) -> dict[str, Any]:
        """
        Parse nuclei stdout JSON-lines output.
        """
        findings = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                info = data.get("info", {})
                template_id = data.get("template-id") or data.get("template_id")
                if not template_id:
                    continue
                # Extract standard fields
                name = info.get("name") or data.get("name") or "unknown"
                severity = info.get("severity") or data.get("severity") or "info"
                matched_at = data.get("matched-at") or data.get("matched_at") or data.get("host") or ""
                description = info.get("description") or data.get("description") or ""

                findings.append({
                    "template_id": template_id,
                    "name": name,
                    "severity": severity,
                    "matched_at": matched_at,
                    "description": description
                })
            except Exception:
                pass

        return {"vulnerabilities": findings}
