from pathlib import Path
import logging
import threading

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Thread-local storage for scan log context
log_context = threading.local()


# ---------------------------------------------------------------------------
# Fix #1 — LogRecordFactory injects defaults into EVERY record globally
# ---------------------------------------------------------------------------
_old_factory = logging.getLogRecordFactory()


def _record_factory(*args, **kwargs):  # type: ignore[no-untyped-def]
    record = _old_factory(*args, **kwargs)
    record.scan_id = getattr(log_context, "scan_id", "-")
    record.workflow = getattr(log_context, "workflow", "-")
    record.step = getattr(log_context, "step", "-")
    record.tool = getattr(log_context, "tool", "-")
    return record


logging.setLogRecordFactory(_record_factory)


# ---------------------------------------------------------------------------
# Fix #2 — Dedicated "bugbounty" logger, NOT the root logger
# ---------------------------------------------------------------------------
_fmt = (
    "%(asctime)s | %(levelname)s | "
    "[%(scan_id)s][%(workflow)s][%(step)s][%(tool)s] | "
    "%(message)s"
)

logger = logging.getLogger("bugbounty")
logger.setLevel(logging.DEBUG)
logger.propagate = False  # never bubble into root

handler_file = logging.FileHandler(LOG_DIR / "bugbounty.log", encoding="utf-8")
handler_stream = logging.StreamHandler()

handler_file.setFormatter(logging.Formatter(_fmt))
handler_stream.setFormatter(logging.Formatter(_fmt))

handler_file.setLevel(logging.DEBUG)
handler_stream.setLevel(logging.INFO)

logger.addHandler(handler_file)
logger.addHandler(handler_stream)


# ---------------------------------------------------------------------------
# Fix #4 — Silence noisy third-party loggers
# ---------------------------------------------------------------------------
logging.getLogger("paramiko").setLevel(logging.WARNING)
logging.getLogger("paramiko.transport").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("google").setLevel(logging.WARNING)