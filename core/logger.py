from pathlib import Path
import logging
import threading

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Thread-local storage for scan log context
log_context = threading.local()


class ContextFilter(logging.Filter):
    """
    Filter to inject scan_id, workflow, step, and tool from thread-local log_context into every LogRecord.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        record.scan_id = getattr(log_context, "scan_id", "N/A")
        record.workflow = getattr(log_context, "workflow", "N/A")
        record.step = getattr(log_context, "step", "N/A")
        record.tool = getattr(log_context, "tool", "N/A")
        return True


# Configure logging format with context placeholders
handler_file = logging.FileHandler(LOG_DIR / "bugbounty.log", encoding="utf-8")
handler_stream = logging.StreamHandler()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | [%(scan_id)s][%(workflow)s][%(step)s][%(tool)s] | %(message)s",
    handlers=[handler_file, handler_stream],
)

logger = logging.getLogger("BugBountyAI")
logger.addFilter(ContextFilter())