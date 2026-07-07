from __future__ import annotations

import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    """Configure structured, production-friendly logging.

    Kept intentionally simple (stdlib) so it works identically inside
    Docker/K8s where logs are collected from stdout, without pulling in
    an extra dependency. Swap the Formatter for JSON if your log
    aggregator (Loki/ELK) prefers structured lines.
    """
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | bot_id=%(bot_id)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.handlers.clear()
    root.addHandler(handler)

    # Quiet down noisy third-party loggers
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)


class BotIdLogFilter(logging.Filter):
    """Injects a default bot_id=- for log records emitted outside a bot context."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "bot_id"):
            record.bot_id = "-"
        return True


logging.getLogger().addFilter(BotIdLogFilter())
