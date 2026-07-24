# Configures a rotating file logger for the entire application.
# All modules import get_logger() from here to use the same named logger.

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Resolve the logs/ directory relative to the project root (one level above core/)
LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)  # create logs/ directory if it doesn't exist
LOG_FILE = LOG_DIR / "app.log"

# Format each log line with timestamp, level, and message
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

# Rotate the log file when it reaches 2 MB, keeping up to 3 backups
handler = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=3)
handler.setFormatter(formatter)

logger = logging.getLogger("multi_agent_ai_system")
logger.setLevel(logging.INFO)
logger.addHandler(handler)
logger.propagate = False  # prevent log records from bubbling up to the root logger


def get_logger():
    """Return the shared application logger instance."""
    return logger
