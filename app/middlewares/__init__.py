from __future__ import annotations

from aiogram import Dispatcher

from app.middlewares.bot_context import BotContextMiddleware
from app.middlewares.db_session import DbSessionMiddleware
from app.middlewares.throttling import ThrottlingMiddleware


def register_middlewares(dp: Dispatcher) -> None:
    """Order matters: DB session must exist before BotContext (which
    queries the DB), and throttling should run before both to reject
    spam as cheaply as possible.
    """
    dp.update.outer_middleware(ThrottlingMiddleware(rate=0.4))
    dp.update.outer_middleware(DbSessionMiddleware())
    dp.update.outer_middleware(BotContextMiddleware())
