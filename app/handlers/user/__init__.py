from __future__ import annotations

from aiogram import Router

from app.handlers.user import captcha, join_request, menu, private_channels, start

user_router = Router(name="user_root")
user_router.include_router(start.router)
user_router.include_router(captcha.router)
user_router.include_router(menu.router)
user_router.include_router(private_channels.router)
user_router.include_router(join_request.router)
