import re
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
        Validate that either a target URL/domain or an input file path is provided.
        """
        if "target" not in kwargs and "input_file" not in kwargs:
            raise ValueError("Either 'target' or 'input_file' must be provided for httpx.")

        if "target" in kwargs:
            target = kwargs["target"]
            if not isinstance(target, str) or not target.strip():
                raise ValueError("'target' must be a non-empty string.")

        if "input_file" in kwargs:
            input_file = kwargs["input_file"]
            if not isinstance(input_file, str) or not input_file.strip():
                raise ValueError("'input_file' must be a non-empty string.")

    def build(self, **kwargs) -> Command:
        """
        Build the httpx execution Command.
        """
        args = ["-sc", "-title", "-o", "-"]
        if "target" in kwargs:
            args.extend(["-u", kwargs["target"]])
        elif "input_file" in kwargs:
            args.extend(["-l", kwargs["input_file"]])
        return Command(executable="httpx", args=args)

    def parse(self, stdout: str) -> dict[str, Any]:
        """
        Parse httpx stdout containing 'url [status_code] [title]' lines.
        """
        results = []
        # Matches: url [status] [title]
        pattern = re.compile(r"^(https?://\S+)(?:\s+\[(\d+)\])?(?:\s+\[(.*?)\])?")

        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            match = pattern.match(line)
            if match:
                url = match.group(1)
                status_code = int(match.group(2)) if match.group(2) else None
                title = match.group(3) if match.group(3) else None
                results.append({
                    "url": url,
                    "status_code": status_code,
                    "title": title
                })

        return {"endpoints": results}
