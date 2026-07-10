from typing import Any

from models.tool import ToolResult


class Normalizer:
    """
    Standardizer that processes command outputs and metadata in ToolResult list
    and extracts a clean list of raw finding dictionaries.
    """

    def normalize(self, results: list[ToolResult]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for res in results:
            tool_name = res.command.executable if res.command else "unknown"
            
            # 1. Parse from structured tool metadata dictionaries
            if res.metadata:
                if "subdomains" in res.metadata:
                    for sub in res.metadata["subdomains"]:
                        normalized.append({
                            "tool": tool_name,
                            "target": str(sub),
                            "data": {"type": "subdomain"},
                            "severity": "info",
                            "description": f"Discovered subdomain: {sub}",
                        })
                    continue
                
                if "alive_hosts" in res.metadata:
                    for host in res.metadata["alive_hosts"]:
                        normalized.append({
                            "tool": tool_name,
                            "target": str(host),
                            "data": {"type": "alive"},
                            "severity": "info",
                            "description": f"Host is alive: {host}",
                        })
                    continue

                if "vulnerabilities" in res.metadata:
                    for vuln in res.metadata["vulnerabilities"]:
                        normalized.append({
                            "tool": tool_name,
                            "target": vuln.get("target", "unknown"),
                            "data": vuln,
                            "severity": vuln.get("severity", "info"),
                            "description": vuln.get("name", "Vulnerability discovered"),
                        })
                    continue

            # 2. Parsing fallback from stdout standard strings directly
            for line in res.stdout.splitlines():
                line_stripped = line.strip()
                if line_stripped:
                    normalized.append({
                        "tool": tool_name,
                        "target": line_stripped,
                        "data": {"raw_line": line_stripped},
                        "severity": "info",
                        "description": f"Raw finding: {line_stripped}",
                    })
                    
        return normalized
