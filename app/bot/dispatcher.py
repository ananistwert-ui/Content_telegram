from __future__ import annotations

from aiogram import Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from app.core.config import settings
from app.handlers.admin import admin_router
from app.handlers.user import user_router
from app.middlewares import register_middlewares


def build_admin_dispatcher() -> Dispatcher:
    """The admin bot needs FSM (multi-step wizards) that survives process
    restarts and works if you ever run >1 worker, hence RedisStorage
    rather than the in-memory default.
    """
    storage = RedisStorage.from_url(settings.REDIS_DSN)
    dp = Dispatcher(storage=storage)
    register_middlewares(dp)
    dp.include_router(admin_router)
    return dp


def build_user_dispatcher() -> Dispatcher:
    """Shared across every child bot. No FSM state is used on the user
    side today (the whole flow is derived from DB state), so the default
    in-memory storage is fine and avoids an extra Redis round trip per
    update.
    """
    dp = Dispatcher()
    register_middlewares(dp)
    dp.include_router(user_router)
    return dp
