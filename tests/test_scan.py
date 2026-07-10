from unittest.mock import MagicMock, patch
import pytest
import tempfile
from pathlib import Path

from bugbounty import scan
from models.report import ScanResult
from core.backend import ExecutionResult


@pytest.fixture
def mock_ssh():
    """
    Mock SSHBackend to return successful tool stdout responses for subfinder, httpx, katana, naabu, and nuclei commands.
    """
    with patch("engine.scan.SSHBackend") as mock_class:
        mock_backend = MagicMock()
        mock_class.return_value = mock_backend

        # Stub SSH run method
        def mock_run(command_obj):
            exe = command_obj.executable
            # Match executable to return mock tool standard output data
            if exe == "subfinder":
                stdout = "sub.example.com\nother.example.com\n"
            elif exe == "httpx":
                stdout = (
                    '{"url":"https://sub.example.com","status_code":200,"title":"Success"}\n'
                    '{"url":"https://other.example.com","status_code":200,"title":"Ready"}'
                )
            elif exe == "katana":
                stdout = "https://sub.example.com/login\nhttps://other.example.com/admin"
            elif exe == "naabu":
                stdout = "sub.example.com:80\nother.example.com:443"
            elif exe == "nuclei":
                stdout = (
                    '{"template-id":"missing-csp","info":{"name":"Missing CSP","severity":"low"},"matched-at":"https://sub.example.com"}\n'
                    '{"template-id":"exposed-git","info":{"name":"Git exposed","severity":"medium"},"matched-at":"https://other.example.com"}'
                )
            else:
                stdout = ""

            return ExecutionResult(
                command=command_obj.shell_escape(),
                stdout=stdout,
                stderr="",
                exit_code=0,
            )

        mock_backend.run.side_effect = mock_run
        yield mock_backend


def test_full_pipeline_scan(mock_ssh):
    """
    Verify that scan() runs the entire engine flow (Planner -> Workflow -> Analyst -> Reporter -> Cleanup) and exits cleanly.
    """
    # Create temporary directory for report outputs
    with tempfile.TemporaryDirectory() as temp_reports:
        # Patch download file step to bypass actual SFTP transfer
        with patch("core.executor.Executor.download"):
            res = scan(
                target="example.com",
                workflow="recon",
                output_dir=temp_reports,
                no_ai=True,
                keep_artifacts=False
            )

            # Assert scan output values
            assert isinstance(res, ScanResult)
            assert res.target == "example.com"
            assert res.success is True
            assert res.duration > 0
            
            # Verify findings were classified and triaged
            findings = res.analysis_result.findings
            assert len(findings) == 10
            nuclei_findings = [f for f in findings if f.tool == "nuclei"]
            assert len(nuclei_findings) == 2
            assert nuclei_findings[0].severity in ["low", "medium"]

            # Verify report output files exist
            md_file = Path(temp_reports) / "report.md"
            json_file = Path(temp_reports) / "report.json"
            assert md_file.exists()
            assert json_file.exists()

            # Verify remote workspace cleanup was executed
            mock_ssh.run.assert_any_call(
                pytest.approx(mock_ssh.run.call_args_list[-1][0][0])
            )
            # The last run command should be rm -rf
            last_cmd = mock_ssh.run.call_args_list[-1][0][0]
            assert "rm -rf" in last_cmd.executable or "rm" in last_cmd.executable
