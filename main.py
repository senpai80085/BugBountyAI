from __future__ import annotations

import argparse
import json
import logging
import sys

from engine.scan import ScanOrchestrator


def main() -> None:
    parser = argparse.ArgumentParser(description="BugBountyAI CLI Scan Engine")
    parser.add_argument("target", help="Target domain, URL, or host to analyze")
    parser.add_argument("--workflow", default=None, help="Forced execution workflow name (e.g. recon)")
    parser.add_argument("--output", default=None, help="Local directory path to store JSON/MD reports")
    parser.add_argument("--json", action="store_true", help="Emit serialized JSON output report to stdout")
    parser.add_argument("--markdown", action="store_true", default=True, help="Generate Markdown output report")
    parser.add_argument("--keep-artifacts", action="store_true", help="Preserve remote workspace files on the Kali box")
    parser.add_argument("--workspace", default=None, help="Remote workspace root prefix override path")
    parser.add_argument("--scan-id", default=None, help="Custom predefined Scan ID UUID")
    parser.add_argument("--no-ai", action="store_true", help="Disable AI provider triaging/validation logic")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose debug logs to stdout")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    orchestrator = ScanOrchestrator()
    try:
        # Override workspace layout inside run_scan if custom path is passed
        scan_result = orchestrator.run_scan(
            target=args.target,
            workflow=args.workflow,
            output_dir=args.output,
            no_ai=args.no_ai,
            verbose=args.verbose,
            keep_artifacts=args.keep_artifacts,
            scan_id=args.scan_id,
        )

        if args.json:
            from core.reporter import to_dict
            print(json.dumps(to_dict(scan_result), indent=2))
        else:
            print("\n" + "=" * 50)
            print("BUGBOUNTYAI SCAN COMPLETED")
            print(f"Scan ID:      {scan_result.scan_id}")
            print(f"Target:       {scan_result.target}")
            print(f"Risk Score:   {scan_result.analysis_result.risk_score.upper()}")
            print(f"Duration:     {scan_result.duration:.2f} seconds")
            print(f"Findings:     {len(scan_result.analysis_result.findings)}")
            print("=" * 50 + "\n")

        sys.exit(0)

    except Exception as e:
        logger = logging.getLogger("BugBountyAI")
        logger.error(f"Execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
