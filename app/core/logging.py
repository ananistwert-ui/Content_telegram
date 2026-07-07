from __future__ import annotations

import logging
import sys

from app.core.config import settings


class BotIdLogFilter(logging.Filter):
    """Injects a default bot_id=- for log records emitted outside a bot context."""
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "bot_id"):
            record.bot_id = "-"
        return True


def setup_logging() -> None:
    """Configure structured, production-friendly logging."""
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)

    handler = logging.StreamHandler(sys.stdout)
    
    # Сначала добавляем фильтр к хендлеру!
    handler.addFilter(BotIdLogFilter())
    
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