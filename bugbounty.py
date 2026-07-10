from __future__ import annotations

from typing import Optional

from engine.scan import scan as engine_scan
from models.report import ScanResult

__all__ = ["scan", "ScanResult"]


def scan(
    target: str,
    workflow: Optional[str] = None,
    output_dir: Optional[str] = None,
    no_ai: bool = False,
    verbose: bool = False,
    keep_artifacts: bool = False,
    scan_id: Optional[str] = None,
) -> ScanResult:
    """
    Public scanning interface. Executes the unified BugBountyAI engine flow.
    """
    return engine_scan(
        target=target,
        workflow=workflow,
        output_dir=output_dir,
        no_ai=no_ai,
        verbose=verbose,
        keep_artifacts=keep_artifacts,
        scan_id=scan_id,
    )
