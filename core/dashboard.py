from __future__ import annotations

import time
import threading
from typing import Any
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

def format_time(seconds: float) -> str:
    """Format seconds into 1m42s or 36s style."""
    if seconds < 0:
        return "0s"
    m, s = divmod(int(seconds), 60)
    if m > 0:
        return f"{m}m{s:02d}s"
    return f"{s}s"

class Dashboard:
    """
    Rich Live Dashboard manager for rendering overall scan progress,
    step execution table, live tool statistics, and scrolling live logs.
    """

    def __init__(self, target: str, scan_id: str, verbose: bool = False) -> None:
        self.target = target
        self.scan_id = scan_id
        self.verbose = verbose
        self.start_time = time.time()

        self.steps: dict[str, dict[str, Any]] = {}
        self.stats = {
            "Subdomains": 0,
            "Alive": 0,
            "Ports": 0,
            "URLs": 0,
            "Findings": 0,
        }
        self.logs: list[Text] = []
        self.total_steps = 0
        self.completed_steps = 0

        self.lock = threading.Lock()
        self.live: Live | None = None

        # Custom console using UTF-8 wrapper to prevent cp1252 exceptions
        import io
        import sys
        is_pytest = "pytest" in sys.modules
        is_utf8 = getattr(sys.stdout, "encoding", "").lower() in ("utf-8", "utf8")

        if hasattr(sys.stdout, "buffer") and not is_pytest and not is_utf8:
            try:
                console_file = io.TextIOWrapper(
                    sys.stdout.buffer,
                    encoding="utf-8",
                    errors="replace",
                    line_buffering=True,
                )
            except Exception:
                console_file = sys.stdout  # type: ignore[assignment]
        else:
            console_file = sys.stdout  # type: ignore[assignment]
        self.console = Console(file=console_file, highlight=False)


    def set_total_steps(self, total: int) -> None:
        with self.lock:
            self.total_steps = total

    def update_step(self, tool: str, status: str, duration: float = 0.0) -> None:
        """Update status and runtime of a workflow step."""
        with self.lock:
            if tool not in self.steps:
                self.steps[tool] = {"status": "pending", "duration": 0.0}
            self.steps[tool]["status"] = status
            if duration > 0:
                self.steps[tool]["duration"] = duration
            if status in ["completed", "failed"]:
                self.completed_steps = sum(
                    1 for s in self.steps.values() if s["status"] in ["completed", "failed"]
                )

    def update_stat(self, name: str, value: int) -> None:
        """Add to or update statistics display."""
        with self.lock:
            if name in self.stats:
                self.stats[name] = value

    def add_log(self, text: Text) -> None:
        """Add formatted log line to scrolling log buffer."""
        with self.lock:
            self.logs.append(text)
            if len(self.logs) > 50:
                self.logs.pop(0)

    def make_layout(self) -> Layout:
        """Build the dashboard layout components."""
        with self.lock:
            layout = Layout()

            # 1. Header info
            header_text = Text()
            header_text.append("BUGBOUNTYAI ACTIVE SCAN\n", style="magenta bold")
            header_text.append(f"Target: {self.target} | Scan ID: {self.scan_id}", style="dim")
            header_panel = Panel(header_text, border_style="dim")

            # 2. Progress and ETA
            pct = 0
            if self.total_steps > 0:
                pct = int((self.completed_steps / self.total_steps) * 100)

            num_bars = int(pct / 10)
            bar_str = "█" * num_bars + "░" * (10 - num_bars)

            elapsed = time.time() - self.start_time
            if self.completed_steps > 0:
                eta = (elapsed / self.completed_steps) * (self.total_steps - self.completed_steps)
            else:
                eta = (self.total_steps - self.completed_steps) * 15.0

            progress_text = Text()
            progress_text.append(f"Recon {bar_str} {pct}%\n\n", style="magenta bold")
            progress_text.append(f"Elapsed : {format_time(elapsed)}\n", style="cyan")
            progress_text.append(f"ETA     : {format_time(eta)}\n", style="yellow")
            progress_panel = Panel(progress_text, title="Overall Progress", border_style="cyan")

            # 3. Live Stats
            stats_table = Table.grid(padding=(0, 2))
            stats_table.add_column("Metric", style="cyan bold")
            stats_table.add_column("Value", style="green")
            for k, v in self.stats.items():
                stats_table.add_row(f"{k}:", str(v))
            stats_panel = Panel(stats_table, title="Live Statistics", border_style="green")

            # 4. Step Table
            step_table = Table(show_header=True, header_style="bold magenta", box=None)
            step_table.add_column("Tool")
            step_table.add_column("Status")
            step_table.add_column("Duration")

            for tool, info in self.steps.items():
                status = info["status"]
                dur = info["duration"]
                dur_str = f"{dur:.1f}s" if dur > 0 else "-"

                if status == "running":
                    status_str = "[yellow]⏳ Running[/yellow]"
                elif status == "completed":
                    status_str = "[green]✓ Completed[/green]"
                elif status == "failed":
                    status_str = "[red]✗ Failed[/red]"
                else:
                    status_str = "[dim]⌛ Pending[/dim]"

                step_table.add_row(tool, status_str, dur_str)
            step_panel = Panel(step_table, title="Workflow Steps", border_style="magenta")

            # Assemble rows
            body = Layout(name="body")
            body.split_row(
                Layout(progress_panel, name="progress", ratio=1),
                Layout(stats_panel, name="stats", ratio=1),
                Layout(step_panel, name="steps", ratio=2),
            )

            if self.verbose:
                # Merge logs
                log_renderable = Text()
                for line in self.logs[-10:]:
                    log_renderable.append_text(line)
                    log_renderable.append("\n")

                layout.split_column(
                    Layout(header_panel, name="header", size=4),
                    body,
                    Layout(Panel(log_renderable, title="Live Logs", border_style="blue"), name="logs", ratio=1),
                )
            else:
                layout.split_column(
                    Layout(header_panel, name="header", size=4),
                    body
                )

            return layout

    def start(self) -> None:
        """Start the dashboard live rendering context."""
        self.live = Live(self.make_layout(), console=self.console, refresh_per_second=4, auto_refresh=False)
        self.live.start()
        # Start a refresh loop thread to update time-based widgets (Elapsed, ETA)
        self._stop_event = threading.Event()
        self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._refresh_thread.start()

    def _refresh_loop(self) -> None:
        while not self._stop_event.is_set():
            if self.live:
                try:
                    self.live.update(self.make_layout(), refresh=True)
                except Exception:
                    pass
            time.sleep(0.5)

    def stop(self) -> None:
        """Stop dashboard live rendering context."""
        if hasattr(self, "_stop_event"):
            self._stop_event.set()
        if hasattr(self, "_refresh_thread"):
            self._refresh_thread.join(timeout=1.0)
        if self.live:
            try:
                self.live.stop()
            except Exception:
                pass
            self.live = None
