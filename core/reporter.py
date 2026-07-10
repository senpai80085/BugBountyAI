from __future__ import annotations

import dataclasses
from datetime import datetime
from enum import Enum
import json
import os
from pathlib import Path
from typing import Any

from models.context import ScanContext
from models.report import AnalysisResult, ReportMetadata, ScanReport, ScanResult


def to_dict(obj: Any) -> Any:
    """
    Recursively convert dataclasses, lists, dicts, datetimes, and enums to json-serializable dicts.
    """
    if dataclasses.is_dataclass(obj):
        res = {}
        for f in dataclasses.fields(obj):
            val = getattr(obj, f.name)
            res[f.name] = to_dict(val)
        return res
    elif isinstance(obj, list):
        return [to_dict(x) for x in obj]
    elif isinstance(obj, dict):
        return {str(k): to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, Enum):
        return obj.value
    else:
        return obj


class Reporter:
    """
    Reporter formats triaged findings and persists them to JSON or Markdown outputs
    directly from ScanResult instances.
    """

    def generate(self, result: AnalysisResult, context: ScanContext) -> ScanReport:
        """
        Legacy interface compatibility method. Returns ScanReport structure.
        """
        metadata = ReportMetadata(
            target=context.target,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        return ScanReport(
            metadata=metadata,
            summary=result.summary,
            findings=result.findings
        )

    def generate_reports(self, scan_result: ScanResult, report_dir: str) -> None:
        """
        Build Markdown and JSON report files and write them to the specified report directory.
        Generates everything from the ScanResult object without reading raw artifact files.
        """
        os.makedirs(report_dir, exist_ok=True)

        # 1. Write JSON Report
        json_path = Path(report_dir) / "report.json"
        json_data = to_dict(scan_result)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=4)

        # 2. Write Markdown Report
        md_path = Path(report_dir) / "report.md"
        
        md_content = []
        md_content.append(f"# BugBountyAI Scan Report - {scan_result.target}\n")
        md_content.append("## 1. Scan Metadata\n")
        md_content.append(f"- **Scan ID:** `{scan_result.scan_id}`")
        md_content.append(f"- **Target:** `{scan_result.target}`")
        md_content.append(f"- **Started At:** `{scan_result.started_at.isoformat()}`")
        md_content.append(f"- **Finished At:** `{scan_result.finished_at.isoformat()}`")
        md_content.append(f"- **Duration:** `{scan_result.duration:.2f} seconds`")
        md_content.append(f"- **Engine Version:** `{scan_result.engine_version}`")
        md_content.append(f"- **Success:** `{scan_result.success}`\n")

        md_content.append("## 2. Executive Summary\n")
        md_content.append(f"- **Overall Risk Score:** `{scan_result.analysis_result.risk_score.upper()}`")
        md_content.append(f"- **Summary:** {scan_result.analysis_result.summary}\n")

        md_content.append("## 3. Discovered Vulnerabilities & Findings\n")
        findings = scan_result.analysis_result.findings
        if findings:
            md_content.append("| Tool | Severity | Description | Target |")
            md_content.append("| :--- | :--- | :--- | :--- |")
            for finding in findings:
                sev_label = finding.severity.value.upper() if hasattr(finding.severity, "value") else str(finding.severity).upper()
                md_content.append(f"| {finding.tool} | `{sev_label}` | {finding.description} | `{finding.target}` |")
            md_content.append("\n")
        else:
            md_content.append("_No vulnerabilities or security issues were identified during this scan._\n")

        md_content.append("## 4. Execution Artifact References\n")
        artifacts = scan_result.artifacts
        if artifacts:
            md_content.append("| ID | Tool | Filename | Size (Bytes) | SHA-256 Checksum | Local Path |")
            md_content.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            for a in artifacts:
                md_content.append(
                    f"| `{a.id[:8]}` | {a.type} | {a.filename} | {a.size} | `{a.checksum[:16]}...` | `{a.local_path}` |"
                )
            md_content.append("\n")
        else:
            md_content.append("_No download artifacts were recorded._\n")

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_content))
