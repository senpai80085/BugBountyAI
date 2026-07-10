import os
from typing import Any

from core.command import Command
from core.executor import Executor
from models.tool import ToolMetadata, ToolResult
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

    def execute(self, executor: Executor, **kwargs: Any) -> ToolResult:
        """
        Execute subfinder, checking for 0 subdomains. If 0 results are found,
        creates 'alive_input.txt' with the target domain as a fallback.
        """
        result = super().execute(executor, **kwargs)

        if result.success:
            subdomains = result.metadata.get("subdomains", [])
            if not subdomains:
                domain = kwargs.get("domain", "")
                output_file = kwargs.get("output_file")
                if output_file:
                    parent_dir = os.path.dirname(output_file)
                    fallback_remote_path = os.path.join(parent_dir, "alive_input.txt").replace("\\", "/")

                    # Create fallback file on remote containing the original target
                    echo_cmd = Command(
                        executable="bash",
                        args=["-c", f"echo '{domain}' > '{fallback_remote_path}'"]
                    )
                    executor.run(echo_cmd)

                    # Register fallback artifact
                    if getattr(executor, "artifact_manager", None) is not None:
                        filename = os.path.basename(fallback_remote_path)
                        fallback_artifact = executor.artifact_manager.register_artifact(
                            artifact_type=self.metadata.name,
                            filename=filename,
                            remote_path=fallback_remote_path
                        )
                        return ToolResult(
                            command=result.command,
                            success=result.success,
                            exit_code=result.exit_code,
                            stdout=result.stdout,
                            stderr=result.stderr,
                            duration=result.duration,
                            artifacts=[fallback_artifact],
                            metadata=result.metadata,
                        )
        return result
