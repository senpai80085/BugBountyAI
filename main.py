from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from engine.scan import ScanOrchestrator
from core.scan_state import ScanState


def main() -> None:
    parser = argparse.ArgumentParser(description="BugBountyAI CLI Scan Engine")
    parser.add_argument("target", help="Target domain, URL, or host to analyze")
    parser.add_argument("--workflow", default=None, help="Forced execution workflow name (e.g. recon)")
    parser.add_argument("--output", default=None, help="Local directory path to store JSON/MD reports")
    parser.add_argument("--json", action="store_true", help="Emit serialized JSON output report to stdout")
    parser.add_argument("--markdown", action="store_true", default=True, help="Generate Markdown output report")
    parser.add_argument("--keep-artifacts", action="store_true", help="Preserve remote workspace files on the Kali box")
    parser.add_argument("--keep-workspace", action="store_true", help="Alias for --keep-artifacts")
    parser.add_argument("--workspace", default=None, help="Remote workspace root prefix override path")
    parser.add_argument("--scan-id", default=None, help="Custom predefined Scan ID UUID")
    parser.add_argument("--no-ai", action="store_true", help="Disable AI provider triaging/validation logic")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose debug logs to stdout")
    parser.add_argument("--resume", action="store_true", help="Resume scan from the last completed step")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Resolve keep_workspace boolean
    keep_workspace = args.keep_artifacts or args.keep_workspace

    # Auto-resume logic: lookup last state if scan-id not specified
    scan_id = args.scan_id
    if args.resume and not scan_id:
        try:
            loot_path = Path("loot")
            if loot_path.exists():
                dirs = [d for d in loot_path.iterdir() if d.is_dir() and (d / "state.json").exists()]
                if dirs:
                    # Sort by mtime of state.json
                    dirs.sort(key=lambda d: (d / "state.json").stat().st_mtime, reverse=True)
                    # Find first matching target
                    for d in dirs:
                        state_tmp = ScanState.load(d.name)
                        if state_tmp and state_tmp.target == args.target:
                            scan_id = d.name
                            break
        except Exception:
            pass

    orchestrator = ScanOrchestrator()
    try:
        scan_result = orchestrator.run_scan(
            target=args.target,
            workflow=args.workflow,
            output_dir=args.output,
            no_ai=args.no_ai,
            verbose=args.verbose,
            keep_artifacts=keep_workspace,
            scan_id=scan_id,
            resume=args.resume,
        )

        if args.json:
            from core.reporter import to_dict
            print(json.dumps(to_dict(scan_result), indent=2))
        else:
            from rich.console import Console
            from rich.table import Table

            console = Console()
            table = Table(title="BUGBOUNTYAI SCAN SUMMARY", show_header=True, header_style="bold magenta")
            table.add_column("Metric", style="cyan bold")
            table.add_column("Value", style="green")

            table.add_row("Scan ID", scan_result.scan_id)
            table.add_row("Target", scan_result.target)
            table.add_row("Risk Score", scan_result.analysis_result.risk_score.upper())
            table.add_row("Total Duration", f"{scan_result.duration:.2f}s")
            table.add_row("Findings Count", str(len(scan_result.analysis_result.findings)))

            # Collect metrics
            if scan_result.metrics:
                m = scan_result.metrics
                table.add_row("Commands Executed", str(len(m.commands_executed)))
                table.add_row("SSH Time", f"{m.ssh_time:.2f}s")
                table.add_row("Tool Execution Time", f"{m.tool_execution_time:.2f}s")
                table.add_row("Downloaded Bytes", f"{m.downloaded_bytes} bytes")
                table.add_row("Remote Workspace Size", f"{m.remote_workspace_size} bytes")
                table.add_row("AI Latency", f"{m.ai_latency:.2f}s")
                table.add_row("AI Tokens Used", str(m.tokens))
                table.add_row("Steps Completed", str(m.steps_completed))
                table.add_row("Steps Failed", str(m.steps_failed))

            console.print("\n")
            console.print(table)
            console.print("\n")

        sys.exit(0)

    except Exception as e:
        logger = logging.getLogger("BugBountyAI")
        logger.error(f"Execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
