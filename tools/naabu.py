from typing import Any

from core.command import Command
from models.tool import ToolMetadata
from tools.base import Tool


class NaabuTool(Tool):
    """
    Tool plugin for naabu, scanning open ports on target hosts.
    """
    metadata = ToolMetadata(
        name="naabu",
        version="1.0.0",
        author="BugBountyAI",
        description="Fast syntax-based port scanner written in Go",
        tags=["recon", "portscan"],
        category="recon",
        requirements=["naabu"],
        supports_parallel=True,
    )

    def validate(self, **kwargs) -> None:
        """
        Validate that target host or IP is provided.
        """
        if "target" not in kwargs:
            raise ValueError("Parameter 'target' is required for naabu.")
        target = kwargs["target"]
        if not isinstance(target, (str, list)):
            raise ValueError("Parameter 'target' must be a string or a list of strings.")
        if isinstance(target, str) and not target.strip():
            raise ValueError("Parameter 'target' must be a non-empty string.")

    def build(self, **kwargs) -> Command:
        """
        Build the naabu execution Command.
        """
        target = kwargs["target"]
        args = []
        if isinstance(target, list):
            for t in target:
                args.extend(["-host", str(t)])
        else:
            args.extend(["-host", target])
        args.extend(["-o", "-"])
        return Command(executable="naabu", args=args)

    def parse(self, stdout: str) -> dict[str, Any]:
        """
        Parse naabu stdout list of open ports ('host:port').
        """
        ports = []
        for line in stdout.splitlines():
            line = line.strip()
            if line:
                parts = line.split(":")
                if len(parts) == 2:
                    ports.append({
                        "host": parts[0],
                        "port": int(parts[1])
                    })
        return {"ports": ports}
