from typing import Any

from core.command import Command
from models.tool import ToolMetadata
from tools.base import Tool


class SubfinderTool(Tool):
    """
    Tool plugin for subfinder, running subdomain enumeration.
    """
    metadata = ToolMetadata(
        name="subfinder",
        version="1.0.0",
        author="BugBountyAI",
        description="Subdomain enumeration tool using passive sources",
        tags=["recon", "subdomains"],
        category="recon",
        requirements=["subfinder"],
        supports_parallel=True,
    )

    def validate(self, **kwargs) -> None:
        """
        Validate that target domain is provided.
        """
        if "domain" not in kwargs:
            raise ValueError("Parameter 'domain' is required for subfinder execution.")
        domain = kwargs["domain"]
        if not isinstance(domain, str) or not domain.strip():
            raise ValueError("Parameter 'domain' must be a non-empty string.")

    def build(self, **kwargs) -> Command:
        """
        Build the subfinder Command execution.
        """
        domain = kwargs["domain"]
        args = ["-d", domain, "-silent"]
        
        # Support optional output_file writing
        if "output_file" in kwargs:
            args.extend(["-o", kwargs["output_file"]])
            
        return Command(executable="subfinder", args=args)

    def parse(self, stdout: str) -> dict[str, Any]:
        """
        Parse subfinder output list of subdomains.
        """
        subdomains = []
        for line in stdout.splitlines():
            line = line.strip()
            if line:
                subdomains.append(line)
        return {"subdomains": subdomains}
