from typing import Any

from core.command import Command
from models.tool import ToolMetadata
from tools.base import Tool


class KatanaTool(Tool):
    """
    Tool plugin for katana, spidering and crawling targets.
    """
    metadata = ToolMetadata(
        name="katana",
        version="1.0.0",
        author="BugBountyAI",
        description="Next-generation web crawling and spidering framework",
        tags=["recon", "crawling"],
        category="recon",
        requirements=["katana"],
        supports_parallel=True,
    )

    def validate(self, **kwargs) -> None:
        """
        Validate that target URL is provided.
        """
        if "target" not in kwargs:
            raise ValueError("Parameter 'target' is required for katana.")
        target = kwargs["target"]
        if not isinstance(target, (str, list)):
            raise ValueError("Parameter 'target' must be a string or a list of strings.")
        if isinstance(target, str) and not target.strip():
            raise ValueError("Parameter 'target' must be a non-empty string.")

    def build(self, **kwargs) -> Command:
        """
        Build the katana execution Command.
        """
        target = kwargs["target"]
        args = []
        if isinstance(target, list):
            for t in target:
                args.extend(["-u", str(t)])
        else:
            args.extend(["-u", target])
        args.extend(["-o", "-"])
        return Command(executable="katana", args=args)

    def parse(self, stdout: str) -> dict[str, Any]:
        """
        Parse katana stdout list of crawled URLs.
        """
        urls = []
        for line in stdout.splitlines():
            line = line.strip()
            if line:
                urls.append(line)
        return {"urls": urls}
