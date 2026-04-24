import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"

formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

handler = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=3)
handler.setFormatter(formatter)

logger = logging.getLogger("multi_agent_ai_system")
logger.setLevel(logging.INFO)
logger.addHandler(handler)
logger.propagate = False


def get_logger():
    return logger
