from __future__ import annotations

from aiogram import Router

from app.handlers.admin import bots, broadcast, captcha, channels, dashboard, menu_buttons, private_channels, stats, welcome

admin_router = Router(name="admin_root")
admin_router.include_router(dashboard.router)
admin_router.include_router(bots.router)
admin_router.include_router(welcome.router)
admin_router.include_router(captcha.router)
admin_router.include_router(menu_buttons.router)
admin_router.include_router(channels.router)
admin_router.include_router(private_channels.router)
admin_router.include_router(broadcast.router)
admin_router.include_router(stats.router)
