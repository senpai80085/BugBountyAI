from datetime import datetime
import json
from pathlib import Path
import tempfile

from core.reporter import Reporter
from models.artifact import Artifact
from models.finding import Finding, Severity
from models.plan import Plan, PlanResult
from models.report import AnalysisResult, ScanResult


def test_reporter_file_generation():
    reporter = Reporter()

    # Define minimal ScanResult mock inputs
    plan = Plan(selected_workflow="recon", execution_strategy="parallel", reasoning="test")
    plan_result = PlanResult(plan=plan, success=True, summary="Plan Success")
    
    findings = [
        Finding(tool="nuclei", target="target", data={}, severity=Severity.HIGH, description="SQL injection")
    ]
    analysis = AnalysisResult(summary="Audit clear", findings=findings, risk_score="high")
    
    artifacts = [
        Artifact(id="art-12345", type="subfinder", filename="subs.txt", remote_path="/tmp/subs.txt", local_path="/local/subs.txt")
    ]

    scan_result = ScanResult(
        scan_id="scan-uuid-1",
        target="example.com",
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
        duration=12.5,
        engine_version="1.0",
        success=True,
        plan_result=plan_result,
        analysis_result=analysis,
        artifacts=artifacts
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        reporter.generate_reports(scan_result, temp_dir)

        # Check that JSON report is written and parseable
        json_path = Path(temp_dir) / "report.json"
        assert json_path.exists()
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data["scan_id"] == "scan-uuid-1"
            assert data["target"] == "example.com"
            assert len(data["analysis_result"]["findings"]) == 1
            assert data["analysis_result"]["findings"][0]["severity"] == "high"

        # Check that Markdown report is written
        md_path = Path(temp_dir) / "report.md"
        assert md_path.exists()
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "example.com" in content
            assert "SQL injection" in content
            assert "scan-uuid-1" in content
