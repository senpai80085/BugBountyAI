import json
from typing import Any

from core.command import Command
from models.tool import ToolMetadata
from tools.base import Tool


class HttpxTool(Tool):
    """
    Tool plugin for httpx, probing target web endpoints.
    """
    metadata = ToolMetadata(
        name="httpx",
        version="1.0.0",
        author="BugBountyAI",
        description="Fast and multi-purpose HTTP toolkit for probing endpoints",
        tags=["recon", "probing", "http"],
        category="recon",
        requirements=["httpx"],
        supports_parallel=True,
    )

    def validate(self, **kwargs) -> None:
        """
        Validate that either a target URL/domain/list or an input file path is provided.
        """
        if "target" not in kwargs and "input_file" not in kwargs:
            raise ValueError("Either 'target' or 'input_file' must be provided for httpx.")

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
        Build the httpx execution Command.
        """
        args = ["-silent", "-json"]
        
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

        return Command(executable="httpx", args=args)

    def parse(self, stdout: str) -> dict[str, Any]:
        """
        Parse httpx stdout containing JSON-lines representation of probed hosts.
        """
        endpoints = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                url = data.get("url")
                if not url:
                    continue
                # Extract HTTP title, status code, technology tags, and length
                status_code = data.get("status_code") or data.get("status-code")
                title = data.get("title")
                techs = data.get("tech") or data.get("technologies") or []
                length = data.get("content_length") or data.get("content-length") or 0

                endpoints.append({
                    "url": url,
                    "status_code": int(status_code) if status_code is not None else None,
                    "title": title,
                    "technologies": list(techs) if isinstance(techs, (list, tuple)) else [],
                    "content_length": int(length) if length is not None else 0
                })
            except Exception:
                pass

        return {"endpoints": endpoints}
