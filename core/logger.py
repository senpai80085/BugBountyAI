from pathlib import Path
import logging

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "bugbounty.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("BugBountyAI")