import concurrent.futures
import re
import threading
import time
from typing import Any
import yaml

from core.config import BASE_DIR
from core.executor import Executor
from core.logger import logger
from core.registry import ToolRegistry
from core.command import Command
from models.context import ScanContext
from models.tool import ToolResult
from models.workflow import Workflow, WorkflowStep


def detect_cycle(steps: list[WorkflowStep]) -> None:
    """
    Perform DFS traversal on workflow step dependencies to detect circular dependencies.
    """
    adj = {step.tool: step.depends_on for step in steps}
    visited = {node: 0 for node in adj}  # 0: unvisited, 1: visiting, 2: visited

    def dfs(node: str) -> None:
        visited[node] = 1
        for dep in adj.get(node, []):
            if dep not in visited:
                continue
            if visited[dep] == 1:
                raise ValueError(f"Circular dependency detected involving '{node}' and '{dep}'")
            if visited[dep] == 0:
                dfs(dep)
        visited[node] = 2

    for node in adj:
        if visited[node] == 0:
            dfs(node)


def lookup_path(path_str: str, context: ScanContext) -> Any:
    """
    Lookup a variable path in ScanContext. Supports targets and nested references.
    """
    if path_str == "target":
        return context.target
    if path_str == "scan_id":
        return context.scan_id

    parts = path_str.split(".")
    tool_name = parts[0]
    
    # Thread-safe context query
    result = context.get_result(tool_name)
    if result is None:
        raise ValueError(f"Value reference '{path_str}' refers to tool '{tool_name}' which has not executed yet.")

    if len(parts) == 1:
        return result

    attr = parts[1]
    if hasattr(result, attr):
        val = getattr(result, attr)
    elif attr in result.metadata:
        val = result.metadata[attr]
    else:
        raise ValueError(f"Attribute/key '{attr}' not found in results of tool '{tool_name}'.")

    for part in parts[2:]:
        if isinstance(val, list) and part.isdigit():
            val = val[int(part)]
        elif isinstance(val, dict) and part in val:
            val = val[part]
        elif hasattr(val, part):
            val = getattr(val, part)
        else:
            raise ValueError(f"Path part '{part}' not found in value '{val}' for reference '{path_str}'.")

    return val


def resolve_val(value: Any, context: ScanContext) -> Any:
    """
    Resolve placeholders in variable definitions. If the value is a single placeholder,
    return the native resolved object (e.g. lists).
    """
    if not isinstance(value, str):
        return value

    val_stripped = value.strip()
    if val_stripped.startswith("{{") and val_stripped.endswith("}}"):
        path_str = val_stripped[2:-2].strip()
        return lookup_path(path_str, context)

    def replacer(match: re.Match) -> str:
        path_str = match.group(1).strip()
        res = lookup_path(path_str, context)
        return str(res) if res is not None else ""

    return re.sub(r"\{\{(.*?)\}\}", replacer, value)


class WorkflowEngine:
    """
    Engine responsible for loading YAML-defined workflows and executing
    their tool steps in sequence or parallel depending on dependencies.
    """

    def __init__(self, registry: ToolRegistry, executor: Executor) -> None:
        self.registry = registry
        self.executor = executor
        self.workflows_dir = BASE_DIR / "workflows"

    def load(self, name: str) -> Workflow:
        """
        Load a workflow structure by name from workflows/ directory,
        validating structure, tool presence, and dependencies.
        """
        workflow_file = self.workflows_dir / f"{name}.yaml"
        if not workflow_file.exists():
            raise FileNotFoundError(f"Workflow '{name}' not found at {workflow_file}")

        with open(workflow_file, "r", encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML format: {e}")

        if not isinstance(data, dict) or "name" not in data or "steps" not in data:
            raise ValueError("Invalid workflow structure: 'name' and 'steps' are required.")

        steps = []
        for step_data in data.get("steps", []):
            if not isinstance(step_data, dict) or "tool" not in step_data:
                raise ValueError("Invalid workflow structure: step is missing 'tool' field.")

            tool_name = step_data["tool"]
            try:
                self.registry.get(tool_name)
            except KeyError:
                raise ValueError(f"Tool '{tool_name}' not found in registry.")

            steps.append(
                WorkflowStep(
                    tool=tool_name,
                    args=step_data.get("args", {}),
                    depends_on=step_data.get("depends_on", []),
                    condition=step_data.get("condition"),
                    parallel=step_data.get("parallel", False),
                    timeout=step_data.get("timeout"),
                    retry=step_data.get("retry", 0),
                    continue_on_error=step_data.get("continue_on_error", False),
                )
            )

        # Detect circular dependencies
        detect_cycle(steps)

        return Workflow(name=data["name"], steps=steps)

    def run(self, workflow: Workflow, context: ScanContext) -> list[ToolResult]:
        """
        Execute workflow steps supporting parallel execution, timeouts, retries,
        and continuous updates to the ScanContext results dict.
        """
        from core.logger import log_context
        log_context.scan_id = context.scan_id
        log_context.workflow = workflow.name
        log_context.step = "N/A"
        log_context.tool = "N/A"
        log_context.total_steps = len(workflow.steps)

        logger.info(f"Workflow started: {workflow.name}")
        start_time = time.perf_counter()

        all_results: list[ToolResult] = []
        completed: set[str] = set()
        failed: set[str] = set()
        running: set[str] = set()

        lock = threading.Lock()

        step_counter: list[int] = [0]

        def execute_step_with_retry(step: WorkflowStep) -> ToolResult:
            from core.logger import log_context
            log_context.scan_id = context.scan_id
            log_context.workflow = workflow.name
            log_context.step = step.tool
            log_context.tool = step.tool
            log_context.total_steps = len(workflow.steps)
            with lock:
                step_counter[0] += 1
                log_context.current_step = step_counter[0]

            logger.info(f"Step started: {step.tool}")
            
            resolved_args = {}
            for k, v in step.args.items():
                resolved_args[k] = resolve_val(v, context)

            tool_class = self.registry.get(step.tool)
            tool_instance = tool_class()

            retries = step.retry
            timeout = step.timeout

            last_res = None
            for attempt in range(retries + 1):
                if attempt > 0:
                    logger.info(f"Retrying step '{step.tool}' (attempt {attempt}/{retries})")

                step_start_time = time.perf_counter()
                try:
                    if timeout is not None:
                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as single_exec:
                            fut = single_exec.submit(tool_instance.execute, self.executor, **resolved_args)
                            last_res = fut.result(timeout=timeout)
                    else:
                        last_res = tool_instance.execute(self.executor, **resolved_args)

                    if last_res.success:
                        logger.info(f"Step completed: {step.tool} in {last_res.duration:.2f}s")
                        return last_res
                except concurrent.futures.TimeoutError:
                    logger.error(f"Step '{step.tool}' timed out after {timeout}s.")
                    last_res = ToolResult(
                        command=tool_instance.build(**resolved_args) if hasattr(tool_instance, "build") else Command(executable=step.tool),
                        success=False,
                        exit_code=-9,
                        stdout="",
                        stderr=f"Step timed out after {timeout}s",
                        duration=float(timeout) if timeout is not None else 0.0,
                        artifacts=[],
                        metadata={"error": "timeout"},
                    )
                except Exception as e:
                    logger.error(f"Step '{step.tool}' failed with error: {e}")
                    last_res = ToolResult(
                        command=tool_instance.build(**resolved_args) if hasattr(tool_instance, "build") else Command(executable=step.tool),
                        success=False,
                        exit_code=-1,
                        stdout="",
                        stderr=str(e),
                        duration=time.perf_counter() - step_start_time,
                        artifacts=[],
                        metadata={"error": str(e)},
                    )

            logger.error(f"Step failed: {step.tool}")
            if last_res is None:
                last_res = ToolResult(
                    command=tool_instance.build(**resolved_args) if hasattr(tool_instance, "build") else Command(executable=step.tool),
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr="Step failed with no execution attempt",
                    duration=0.0,
                    artifacts=[],
                    metadata={"error": "no attempt made"},
                )
            return last_res

        with concurrent.futures.ThreadPoolExecutor() as pool:
            futures = {}

            while len(completed) + len(failed) < len(workflow.steps):
                ready_steps = []
                for step in workflow.steps:
                    if step.tool in completed or step.tool in failed or step.tool in running:
                        continue

                    deps_ok = True
                    dep_failed = False
                    for dep in step.depends_on:
                        if dep in failed:
                            dep_failed = True
                            break
                        if dep not in completed:
                            deps_ok = False
                            break

                    if dep_failed:
                        logger.error(f"Step '{step.tool}' is blocked by failed dependency.")
                        with lock:
                            failed.add(step.tool)
                        continue

                    if deps_ok:
                        ready_steps.append(step)

                # Submit ready steps to the thread pool
                for step in ready_steps:
                    with lock:
                        running.add(step.tool)
                    fut = pool.submit(execute_step_with_retry, step)
                    futures[fut] = step

                if not futures:
                    if len(completed) + len(failed) < len(workflow.steps):
                        logger.error("Deadlock or unresolved dependencies detected in workflow execution loop.")
                        break
                    break

                done, _ = concurrent.futures.wait(futures.keys(), return_when=concurrent.futures.FIRST_COMPLETED)
                for fut in done:
                    step = futures.pop(fut)
                    tool_name = step.tool
                    with lock:
                        running.remove(tool_name)

                    try:
                        result = fut.result()
                        all_results.append(result)
                        
                        # Thread-safe context update
                        context.set_result(tool_name, result)

                        if result.success:
                            with lock:
                                completed.add(tool_name)
                        else:
                            if step.continue_on_error:
                                with lock:
                                    completed.add(tool_name)
                            else:
                                with lock:
                                    failed.add(tool_name)
                    except Exception as e:
                        logger.error(f"Execution thread raised critical exception for '{tool_name}': {e}")
                        with lock:
                            failed.add(tool_name)

        workflow_duration = time.perf_counter() - start_time
        logger.info(f"Workflow completed: {workflow.name} in {workflow_duration:.2f}s")
        return all_results
