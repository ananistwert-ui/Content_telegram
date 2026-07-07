from __future__ import annotations
<<<<<<< HEAD

import logging
import sys

from app.core.config import settings


class BotIdLogFilter(logging.Filter):
    """Injects a default bot_id=- for log records emitted outside a bot context."""
=======
import logging
import sys
from app.core.config import settings

class BotIdLogFilter(logging.Filter):
    """Фильтр для добавления bot_id в записи лога, если он отсутствует."""
>>>>>>> 4c2f3e7 (fix: resolve Enum/Postgres type errors, fix logger context, fix webhook startup sequence)
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "bot_id"):
            record.bot_id = "-"
        return True

<<<<<<< HEAD

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
=======
def setup_logging() -> None:
    """Настройка структурированного логирования для production."""
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)

    # Создаем потоковый обработчик (вывод в консоль)
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(BotIdLogFilter())
    handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | bot_id=%(bot_id)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    # Очищаем стандартные обработчики и добавляем наш
    root.handlers.clear()
    root.addHandler(handler)

    # Уменьшаем уровень шума сторонних библиотек, чтобы не засорять логи
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
>>>>>>> 4c2f3e7 (fix: resolve Enum/Postgres type errors, fix logger context, fix webhook startup sequence)
