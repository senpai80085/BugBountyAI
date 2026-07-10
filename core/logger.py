"""
Logging configuration for BugBountyAI.

Provides a thread-safe logger with:
- File handler: structured format with scan context (always active).
- Console handler: Rich-powered color-coded output with elapsed time,
  progress tracking, and spinner animation. Falls back to plain
  StreamHandler when Rich is unavailable.

The logger API (logger.info, logger.error, etc.) is unchanged.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Thread-local storage for scan log context
log_context = threading.local()


# ---------------------------------------------------------------------------
# LogRecordFactory — injects context defaults into EVERY record
# ---------------------------------------------------------------------------
_old_factory = logging.getLogRecordFactory()


def _record_factory(*args, **kwargs):  # type: ignore[no-untyped-def]
    """Inject scan context and progress fields into every LogRecord."""
    record = _old_factory(*args, **kwargs)
    record.scan_id = getattr(log_context, "scan_id", "-")
    record.workflow = getattr(log_context, "workflow", "-")
    record.step = getattr(log_context, "step", "-")
    record.tool = getattr(log_context, "tool", "-")
    record.total_steps = getattr(log_context, "total_steps", 0)
    record.current_step = getattr(log_context, "current_step", 0)
    return record


logging.setLogRecordFactory(_record_factory)


# ---------------------------------------------------------------------------
# Rich Console Handler
# ---------------------------------------------------------------------------
try:
    from rich.console import Console
    from rich.text import Text

    class RichLogHandler(logging.Handler):
        """
        Color-coded logging handler built on Rich.

        Color mapping:
            INFO      → Cyan
            SUCCESS   → Green  (Step completed / Workflow completed)
            WARNING   → Yellow
            ERROR     → Red
            COMMAND   → Blue   (Command started / finished)
            WORKFLOW  → Magenta
            TOOL      → Bright White (Step started)

        Features:
            - Elapsed time column
            - Animated spinner on heartbeat messages
            - Step progress counter [N/T]
        """

        SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

        def __init__(self) -> None:
            super().__init__()
            # Windows defaults stdout to cp1252 which cannot encode Unicode
            # icons. Wrap the raw buffer in a UTF-8 TextIOWrapper so Rich can
            # safely write spinner frames, check marks, and emoji.
            import io
            import sys

            if hasattr(sys.stdout, "buffer"):
                console_file = io.TextIOWrapper(
                    sys.stdout.buffer,
                    encoding="utf-8",
                    errors="replace",
                    line_buffering=True,
                )
            else:
                console_file = sys.stdout  # type: ignore[assignment]
            self.console = Console(file=console_file, highlight=False)
            self.start_time = time.time()
            self._spinner_idx = 0

        def emit(self, record: logging.LogRecord) -> None:
            """Format and print a single log record with Rich styling."""
            try:
                msg = record.getMessage()
                elapsed = time.time() - self.start_time
                elapsed_str = self._format_elapsed(elapsed)
                style, prefix = self._classify(record, msg)

                # Strip 'export PATH=…;' prefix for cleaner command display
                display_msg = msg
                if "export PATH=" in display_msg and "; " in display_msg:
                    display_msg = display_msg.split("; ", 1)[1]

                line = Text()
                line.append(f"[{elapsed_str}] ", style="dim")
                line.append(f"{prefix} ", style=style)

                # Preserve multi-line structure for error blocks
                if "\n" in display_msg:
                    line.append("\n")
                    for sub in display_msg.splitlines():
                        line.append(f"  {sub}\n", style=style)
                else:
                    line.append(display_msg, style=style)

                self.console.print(line)
            except Exception:
                self.handleError(record)

        # -- helpers ---------------------------------------------------------

        @staticmethod
        def _format_elapsed(seconds: float) -> str:
            """Right-aligned elapsed timestamp."""
            if seconds < 60:
                return f"{seconds:6.1f}s"
            m, s = divmod(int(seconds), 60)
            return f"{m:3d}m{s:02d}s"

        def _classify(
            self, record: logging.LogRecord, msg: str
        ) -> tuple[str, str]:
            """Return (rich_style, prefix_icon) based on level and content."""
            # ------- ERROR / WARNING levels -------
            if record.levelno >= logging.ERROR:
                return "red bold", "✗"
            if record.levelno >= logging.WARNING:
                return "yellow", "⚠"

            # ------- INFO: content-based classification -------

            # Heartbeat spinner
            if "[RUNNING]" in msg:
                frame = self.SPINNER_FRAMES[
                    self._spinner_idx % len(self.SPINNER_FRAMES)
                ]
                self._spinner_idx += 1
                return "yellow", frame

            # Commands (blue)
            if "Command started" in msg:
                return "blue", "▶"
            if "Command finished" in msg:
                return "blue", "■"

            # Workflow (magenta)
            if "Workflow started" in msg:
                return "magenta bold", "◆"
            if "Workflow completed" in msg:
                return "magenta", "◆"

            # Tool steps (bright white / green)
            if "Step started" in msg:
                total = getattr(record, "total_steps", 0)
                current = getattr(record, "current_step", 0)
                if total > 0 and current > 0:
                    return "bright_white bold", f"[{current}/{total}]"
                return "bright_white bold", "●"

            if "Step completed" in msg:
                return "green bold", "✓"

            if "Step failed" in msg:
                return "red bold", "✗"

            # Artifacts
            if "Registered remote artifact" in msg:
                return "green", "📦"
            if "Downloading remote artifact" in msg:
                return "cyan", "⬇"

            # SSH lifecycle
            if "SSH connected" in msg or "Connecting to" in msg:
                return "cyan", "⚡"
            if "SSH disconnected" in msg:
                return "cyan dim", "⚡"

            # Reports / cleanup
            if "Reports successfully" in msg:
                return "green bold", "📄"
            if "Cleaning remote workspace" in msg:
                return "cyan dim", "🧹"

            # Retries
            if "Retrying step" in msg:
                return "yellow", "↻"

            # Default INFO
            return "cyan", "ℹ"

    _use_rich = True
except ImportError:
    _use_rich = False


# ---------------------------------------------------------------------------
# Dedicated "bugbounty" logger (NOT the root logger)
# ---------------------------------------------------------------------------
_fmt = (
    "%(asctime)s | %(levelname)s | "
    "[%(scan_id)s][%(workflow)s][%(step)s][%(tool)s] | "
    "%(message)s"
)

logger = logging.getLogger("bugbounty")
logger.setLevel(logging.DEBUG)
logger.propagate = False

# File handler — always uses structured plain-text format
handler_file = logging.FileHandler(LOG_DIR / "bugbounty.log", encoding="utf-8")
handler_file.setFormatter(logging.Formatter(_fmt))
handler_file.setLevel(logging.DEBUG)
logger.addHandler(handler_file)

# Console handler — Rich when available, plain StreamHandler otherwise
if _use_rich:
    handler_stream: logging.Handler = RichLogHandler()
else:
    handler_stream = logging.StreamHandler()
    handler_stream.setFormatter(logging.Formatter(_fmt))

handler_stream.setLevel(logging.INFO)
logger.addHandler(handler_stream)


# ---------------------------------------------------------------------------
# Silence noisy third-party loggers
# ---------------------------------------------------------------------------
logging.getLogger("paramiko").setLevel(logging.WARNING)
logging.getLogger("paramiko.transport").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("google").setLevel(logging.WARNING)