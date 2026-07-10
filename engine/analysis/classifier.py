from typing import Any

from models.finding import Finding, Severity


class Classifier:
    """
    Classifies raw standardized dictionary data into strongly typed Finding objects,
    mapping severity values to the Severity Enum.
    """

    def classify(self, raw_findings: list[dict[str, Any]]) -> list[Finding]:
        findings = []
        for raw in raw_findings:
            sev_str = str(raw.get("severity", "info")).lower()
            
            if "critical" in sev_str:
                severity = Severity.CRITICAL
            elif "high" in sev_str:
                severity = Severity.HIGH
            elif "medium" in sev_str:
                severity = Severity.MEDIUM
            elif "low" in sev_str:
                severity = Severity.LOW
            else:
                severity = Severity.INFO

            findings.append(
                Finding(
                    tool=raw.get("tool", "unknown"),
                    target=raw.get("target", "unknown"),
                    data=raw.get("data", {}),
                    severity=severity,
                    description=raw.get("description", ""),
                )
            )
        return findings
