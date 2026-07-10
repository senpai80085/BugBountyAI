from __future__ import annotations

from datetime import datetime
import time
from typing import Optional
import uuid

from core.logger import log_context, logger
from core.registry import registry
from core.executor import Executor
from core.backend import SSHBackend
from core.artifacts import ArtifactManager
from core.reporter import Reporter
from core.prompt_manager import PromptManager
from engine.planner import Planner
from engine.workflow import WorkflowEngine
from engine.analyst import Analyst
from models.context import ScanContext
from models.objective import Objective, PlanningMode
from models.report import ScanResult
from providers.gemini import GeminiProvider


class ScanOrchestrator:
    """
    Coordinates and drives the entire bug bounty scanner pipeline:
    context setup, execution backends, tool workflows, triaging, and reporting.
    """

    def run_scan(
        self,
        target: str,
        workflow: Optional[str] = None,
        output_dir: Optional[str] = None,
        no_ai: bool = False,
        verbose: bool = False,
        keep_artifacts: bool = False,
        scan_id: Optional[str] = None,
    ) -> ScanResult:
        started_at = datetime.utcnow()
        start_time = time.perf_counter()

        # 1. Initialize Scan ID and log context
        scan_id = scan_id or str(uuid.uuid4())
        log_context.scan_id = scan_id
        log_context.workflow = "N/A"
        log_context.step = "N/A"
        log_context.tool = "N/A"

        logger.info(f"[{scan_id}] Initiating scan for target: {target}")

        # Determine output directories
        report_dir = output_dir or f"reports/{target}"
        loot_dir = f"loot/{scan_id}"
        workspace = f"/tmp/bugbounty/{scan_id}"

        # 2. Construct ScanContext
        context = ScanContext(
            scan_id=scan_id,
            target=target,
            workspace=workspace,
            loot_dir=loot_dir,
            report_dir=report_dir,
        )

        # 3. Setup Executor and backend
        backend = SSHBackend()
        executor = Executor(backend)

        # 4. Instantiate ArtifactManager and bind to Executor
        artifact_manager = ArtifactManager(executor, scan_id)
        executor.artifact_manager = artifact_manager

        # 5. Create remote workspace directory
        artifact_manager.create_workspace()

        plan_result = None
        analysis_result = None
        downloaded_artifacts = []

        try:
            # 6. Discover tools and build execution engine components
            registry.discover()
            workflow_engine = WorkflowEngine(registry, executor)

            # Setup AI components if not disabled
            provider = None
            prompt_manager = None
            if not no_ai:
                try:
                    provider = GeminiProvider()
                    prompt_manager = PromptManager()
                except Exception as e:
                    logger.warning(f"Failed to initialize AI Provider/Prompts: {e}. Falling back to rule-based logic.")

            planner = Planner(registry, workflow_engine, provider, executor)
            analyst = Analyst(provider, prompt_manager)
            reporter = Reporter()

            # Define Objective based on whether custom workflow is forced
            if workflow:
                objective = Objective(
                    text=f"Scan {target} using workflow {workflow}",
                    mode=PlanningMode.MANUAL,
                    suggested_workflow=workflow,
                )
            else:
                objective = Objective(
                    text=f"Scan {target} and audit open vulnerabilities",
                    mode=PlanningMode.AUTO,
                )

            # 7. Run Planner (which executes the workflow internally)
            plan_result = planner.run(objective, context)

            # 8. Run Analyst triage
            analysis_result = analyst.analyze(plan_result.results, context)

            # 9. Download registered remote artifacts locally
            for res in plan_result.results:
                for a in res.artifacts:
                    try:
                        updated_artifact = artifact_manager.download_artifact(a.id, loot_dir)
                        downloaded_artifacts.append(updated_artifact)
                    except Exception as err:
                        logger.error(f"Failed to download remote artifact {a.filename}: {err}")

            # 10. Generate Markdown and JSON Reports from ScanResult
            finished_at = datetime.utcnow()
            duration = time.perf_counter() - start_time

            scan_result = ScanResult(
                scan_id=scan_id,
                target=target,
                started_at=started_at,
                finished_at=finished_at,
                duration=duration,
                engine_version="1.0",
                success=plan_result.success,
                plan_result=plan_result,
                analysis_result=analysis_result,
                artifacts=downloaded_artifacts,
            )

            reporter.generate_reports(scan_result, report_dir)
            logger.info(f"[{scan_id}] Reports successfully written to: {report_dir}")

            return scan_result

        finally:
            # 11. Remote cleanup unless requested otherwise
            if not keep_artifacts:
                try:
                    artifact_manager.cleanup()
                except Exception as err:
                    logger.error(f"Error executing workspace cleanup: {err}")

            # Close SSH connection
            try:
                backend.close()
            except Exception:
                pass
