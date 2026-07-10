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
        if not isinstance(target, str) or not target.strip():
            raise ValueError("Parameter 'target' must be a non-empty string.")

    def build(self, **kwargs) -> Command:
        """
        Build the katana execution Command.
        """
        target = kwargs["target"]
        return Command(executable="katana", args=["-u", target, "-o", "-"])

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
