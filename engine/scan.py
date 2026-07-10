from __future__ import annotations

import time
from datetime import datetime
from typing import Optional
import uuid

from core.logger import log_context, logger, set_dashboard
from core.registry import registry
from core.executor import Executor
from core.backend import SSHBackend, Command
from core.artifacts import ArtifactManager
from core.reporter import Reporter
from core.prompt_manager import PromptManager
from core.dashboard import Dashboard
from core.scan_state import ScanState
from engine.planner import Planner
from engine.workflow import WorkflowEngine
from engine.analyst import Analyst
from models.context import ScanContext
from models.objective import Objective, PlanningMode
from models.report import ScanResult, AnalysisResult
from models.metrics import ScanMetrics
from models.tool import ToolResult
from models.plan import Plan, PlanResult
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
        resume: bool = False,
    ) -> ScanResult:
        started_at = datetime.utcnow()
        start_time = time.perf_counter()

        # 1. Initialize Scan ID
        scan_id = scan_id or str(uuid.uuid4())
        log_context.scan_id = scan_id
        log_context.workflow = "N/A"
        log_context.step = "N/A"
        log_context.tool = "N/A"

        # Determine output directories
        report_dir = output_dir or f"reports/{target}"
        loot_dir = f"loot/{scan_id}"
        workspace = f"/tmp/bugbounty/{scan_id}"

        # 2. Resumable Scan State Load
        state = None
        if resume:
            state = ScanState.load(scan_id)
            if state:
                logger.info(f"Resuming scan {scan_id} for target {target}")
                target = state.target
                workspace = state.workspace

        if state is None:
            state = ScanState(scan_id=scan_id, target=target, workflow=workflow or "recon", workspace=workspace)

        logger.info(f"[{scan_id}] Initiating scan for target: {target}")

        # 3. Setup ScanContext
        context = ScanContext(
            scan_id=scan_id,
            target=target,
            workspace=workspace,
            loot_dir=loot_dir,
            report_dir=report_dir,
        )

        # 4. Instantiate Metrics
        metrics = ScanMetrics()
        metrics.total_scan_duration = 0.0

        # 5. Setup Executor and pooled backend
        backend = SSHBackend()
        # Bind metrics context to backend
        setattr(backend, "metrics", metrics)
        executor = Executor(backend)
        # Bind metrics context to executor
        setattr(executor, "metrics", metrics)

        # 6. Instantiate ArtifactManager and bind to Executor
        artifact_manager = ArtifactManager(executor, scan_id)
        executor.artifact_manager = artifact_manager

        # 7. Create remote workspace directory
        artifact_manager.create_workspace()

        # 8. Start Dashboard
        dashboard = Dashboard(target, scan_id, verbose=verbose)
        set_dashboard(dashboard)
        dashboard.start()

        plan_result = None
        analysis_result = None
        downloaded_artifacts = []

        try:
            # 9. Discover tools and build execution engine components
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

            # Record execution dependency graph
            wf_name = workflow or "recon"
            try:
                loaded_wf = workflow_engine.load(wf_name)
                graph = {step.tool: step.depends_on for step in loaded_wf.steps}
                metrics.set_execution_graph(graph)
            except Exception:
                pass

            # Define Objective based on manual vs. auto mode
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

            # Continuous Reporting Callback
            def step_callback(tool_name: str, result: ToolResult) -> None:
                # Save step progress to state checkpoint
                state.add_completed_step(tool_name, result)
                state.save()

                # Sync/download only new non-empty remote artifacts
                for a in result.artifacts:
                    if a.size > 0:
                        try:
                            artifact_manager.download_artifact(a.id, loot_dir)
                        except Exception as err:
                            logger.error(f"Failed to download remote artifact {a.filename}: {err}")

                # Gather completed results and run analyst triage
                current_results = list(context.results.values())
                curr_duration = time.perf_counter() - start_time

                # Track completed/failed counts in metrics
                completed_count = sum(1 for r in current_results if r.success)
                failed_count = sum(1 for r in current_results if not r.success)
                metrics.steps_completed = completed_count
                metrics.steps_failed = failed_count

                try:
                    curr_analysis = analyst.analyze(current_results, context)
                except Exception:
                    curr_analysis = AnalysisResult(summary="Analysis in progress", findings=[])

                # Construct intermediate ScanResult
                dummy_plan = Plan(selected_workflow=state.workflow, execution_strategy="parallel", reasoning="Resumable scan")
                dummy_plan_res = PlanResult(plan=dummy_plan, success=False, summary="In progress", results=current_results)

                temp_scan_result = ScanResult(
                    scan_id=scan_id,
                    target=target,
                    started_at=started_at,
                    finished_at=datetime.utcnow(),
                    duration=curr_duration,
                    engine_version="1.0",
                    success=False,
                    plan_result=dummy_plan_res,
                    analysis_result=curr_analysis,
                    artifacts=artifact_manager.export(),
                    metrics=metrics,
                )

                try:
                    reporter.generate_reports(temp_scan_result, report_dir)
                except Exception as err:
                    logger.error(f"Failed to write continuous reports: {err}")

            # 10. Run Planner (triggers workflow execution internally)
            plan_result = planner.run(
                objective,
                context,
                scan_state=state,
                step_callback=step_callback,
            )

            # 11. Run Final Analyst triage
            analysis_result = analyst.analyze(plan_result.results, context)

            # 12. Final downloads of registered remote artifacts locally
            for res in plan_result.results:
                for a in res.artifacts:
                    if a.size > 0:
                        try:
                            updated_artifact = artifact_manager.download_artifact(a.id, loot_dir)
                            downloaded_artifacts.append(updated_artifact)
                        except Exception as err:
                            logger.error(f"Failed to download remote artifact {a.filename}: {err}")

            # 13. Measure remote workspace size at the end
            try:
                du_cmd = Command(executable="du", args=["-sb", workspace])
                res_du = executor.run(du_cmd)
                if res_du.exit_code == 0:
                    parts = res_du.stdout.split()
                    if parts:
                        metrics.remote_workspace_size = int(parts[0].strip())
            except Exception:
                pass

            # 14. Gather AI metrics (tokens and latency)
            if provider and isinstance(provider, GeminiProvider):
                metrics.tokens = getattr(provider, "total_tokens", 0)
                metrics.ai_latency = getattr(provider, "total_latency", 0.0)

            # Track completed steps inside metrics
            completed_count = sum(1 for r in plan_result.results if r.success)
            failed_count = sum(1 for r in plan_result.results if not r.success)
            metrics.steps_completed = completed_count
            metrics.steps_failed = failed_count
            metrics.artifact_count = len(artifact_manager.artifacts)

            # Estimate total downloaded bytes
            metrics.downloaded_bytes = sum(a.size for a in artifact_manager.artifacts.values() if a.local_path)

            finished_at = datetime.utcnow()
            duration = time.perf_counter() - start_time
            metrics.total_scan_duration = duration

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
                artifacts=artifact_manager.export(),
                metrics=metrics,
            )

            # Write final reports
            reporter.generate_reports(scan_result, report_dir)
            logger.info(f"[{scan_id}] Reports successfully written to: {report_dir}")

            return scan_result

        finally:
            # 15. Stop Live Dashboard
            set_dashboard(None)
            dashboard.stop()

            # 16. Remote cleanup unless requested otherwise
            if not keep_artifacts:
                try:
                    artifact_manager.cleanup()
                except Exception as err:
                    logger.error(f"Error executing workspace cleanup: {err}")

            # Close SSH connections in pool
            try:
                backend.close()
            except Exception:
                pass


def scan(
    target: str,
    workflow: Optional[str] = None,
    output_dir: Optional[str] = None,
    no_ai: bool = False,
    verbose: bool = False,
    keep_artifacts: bool = False,
    scan_id: Optional[str] = None,
    resume: bool = False,
) -> ScanResult:
    """
    Exposed functional scanner entry point.
    """
    orchestrator = ScanOrchestrator()
    return orchestrator.run_scan(
        target=target,
        workflow=workflow,
        output_dir=output_dir,
        no_ai=no_ai,
        verbose=verbose,
        keep_artifacts=keep_artifacts,
        scan_id=scan_id,
        resume=resume,
    )
