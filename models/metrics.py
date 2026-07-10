from dataclasses import dataclass, field
import threading

@dataclass
class ScanMetrics:
    """
    Thread-safe model representing all execution and performance metrics 
    collected during a scan.
    """
    commands_executed: list[str] = field(default_factory=list)
    ssh_time: float = 0.0
    tool_execution_time: float = 0.0
    downloaded_bytes: int = 0
    remote_workspace_size: int = 0
    ai_latency: float = 0.0
    tokens: int = 0
    total_scan_duration: float = 0.0
    total_requests: int = 0
    artifact_count: int = 0
    steps_completed: int = 0
    steps_failed: int = 0
    execution_graph: dict[str, list[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_lock", threading.Lock())

    def add_command(self, cmd: str) -> None:
        """Record an executed command thread-safely."""
        lock: threading.Lock = getattr(self, "_lock")
        with lock:
            self.commands_executed.append(cmd)

    def add_ssh_time(self, duration: float) -> None:
        """Add SSH/network wait duration thread-safely."""
        lock: threading.Lock = getattr(self, "_lock")
        with lock:
            self.ssh_time += duration

    def add_tool_execution_time(self, duration: float) -> None:
        """Add tool run duration thread-safely."""
        lock: threading.Lock = getattr(self, "_lock")
        with lock:
            self.tool_execution_time += duration

    def add_downloaded_bytes(self, num_bytes: int) -> None:
        """Accumulate local download bytes thread-safely."""
        lock: threading.Lock = getattr(self, "_lock")
        with lock:
            self.downloaded_bytes += num_bytes

    def add_ai_latency(self, duration: float) -> None:
        """Add AI inference latency thread-safely."""
        lock: threading.Lock = getattr(self, "_lock")
        with lock:
            self.ai_latency += duration

    def add_tokens(self, count: int) -> None:
        """Accumulate token counts thread-safely."""
        lock: threading.Lock = getattr(self, "_lock")
        with lock:
            self.tokens += count

    def add_request(self) -> None:
        """Increment request counters thread-safely."""
        lock: threading.Lock = getattr(self, "_lock")
        with lock:
            self.total_requests += 1

    def set_execution_graph(self, graph: dict[str, list[str]]) -> None:
        """Record the dependency execution graph thread-safely."""
        lock: threading.Lock = getattr(self, "_lock")
        with lock:
            self.execution_graph = graph
