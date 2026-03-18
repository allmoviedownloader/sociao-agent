"""
Logger module - Centralized logging for the agent.
"""
import logging
import sys
from pathlib import Path
from collections import deque

# In-memory log buffer for /logs command
LOG_BUFFER = deque(maxlen=100)


class TelegramLogHandler(logging.Handler):
    """Custom handler that stores logs in memory for Telegram /logs command."""

    def emit(self, record):
        log_entry = self.format(record)
        LOG_BUFFER.append(log_entry)


def setup_logger(name: str = "agent") -> logging.Logger:
    """Set up and return the main logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Format
    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # File handler
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "agent.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    # In-memory handler (for /logs command)
    mem_handler = TelegramLogHandler()
    mem_handler.setLevel(logging.INFO)
    mem_handler.setFormatter(fmt)
    logger.addHandler(mem_handler)

    return logger


def get_recent_logs(count: int = 20) -> str:
    """Get recent log entries as a string."""
    logs = list(LOG_BUFFER)[-count:]
    if not logs:
        return "📭 No recent logs."
    return "\n".join(logs)


# Global logger instance
logger = setup_logger()
