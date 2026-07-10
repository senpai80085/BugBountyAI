from typing import Any


class Deduplicator:
    """
    Filters redundant normalized finding raw dictionaries based on combined signatures.
    """

    def deduplicate(self, raw_findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen = set()
        deduplicated = []
        for raw in raw_findings:
            sig = (
                str(raw.get("tool", "")),
                str(raw.get("target", "")),
                str(raw.get("description", "")).strip().lower(),
            )
            if sig not in seen:
                seen.add(sig)
                deduplicated.append(raw)
        return deduplicated
