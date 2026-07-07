from __future__ import annotations

import logging

<<<<<<< HEAD
from aiogram import Bot
=======
from aiogram import Bot, Dispatcher
>>>>>>> 4c2f3e7 (fix: resolve Enum/Postgres type errors, fix logger context, fix webhook startup sequence)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update
from aiohttp import web

from app.bot.bot_manager import bot_manager
from app.bot.dispatcher import build_admin_dispatcher, build_user_dispatcher
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import AsyncSessionFactory
from app.models.bot import Bot as BotModel, BotConfig
from app.repositories.bot_repository import BotRepository

logger = logging.getLogger(__name__)

WEBHOOK_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"

admin_dp = build_admin_dispatcher()
user_dp = build_user_dispatcher()
admin_bot = Bot(token=settings.ADMIN_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


def _check_secret(request: web.Request) -> bool:
    return request.headers.get(WEBHOOK_SECRET_HEADER) == settings.WEBHOOK_SECRET


async def handle_admin_webhook(request: web.Request) -> web.Response:
    if not _check_secret(request):
        return web.Response(status=401)
    update = Update.model_validate(await request.json(), context={"bot": admin_bot})
    await admin_dp.feed_update(admin_bot, update)
    return web.Response()


async def handle_child_webhook(request: web.Request) -> web.Response:
    if not _check_secret(request):
        return web.Response(status=401)
<<<<<<< HEAD
=======
    
>>>>>>> 4c2f3e7 (fix: resolve Enum/Postgres type errors, fix logger context, fix webhook startup sequence)
    try:
        db_bot_id = int(request.match_info["bot_id"])
    except ValueError:
        return web.Response(status=404)

    bot = await bot_manager.get(db_bot_id)
    if bot is None:
        return web.Response(status=404)

    update = Update.model_validate(await request.json(), context={"bot": bot})
    await user_dp.feed_update(bot, update)
    return web.Response()


async def healthcheck(_: web.Request) -> web.Response:
    return web.Response(text="ok")


async def on_startup(app: web.Application) -> None:
    setup_logging()
<<<<<<< HEAD
    logger.info("Starting up: ensuring master admin bot row + webhook are registered")

    async with AsyncSessionFactory() as session:
        repo = BotRepository(session)
=======
    logger.info("Starting up: initializing system...")

    async with AsyncSessionFactory() as session:
        repo = BotRepository(session)
        
        # 1. Регистрация мастер-бота
>>>>>>> 4c2f3e7 (fix: resolve Enum/Postgres type errors, fix logger context, fix webhook startup sequence)
        existing = await repo.get_by_token(settings.ADMIN_BOT_TOKEN)
        if existing is None:
            me = await admin_bot.get_me()
            db_bot = BotModel(
                token=settings.ADMIN_BOT_TOKEN,
                username=me.username,
                display_name="Master Admin Bot",
                is_master=True,
                is_active=True,
            )
            repo.add(db_bot)
            await repo.flush()
            db_bot.config = BotConfig(bot_id=db_bot.id, welcome_caption="Admin bot", captcha_enabled=False)
            session.add(db_bot.config)
            await session.commit()
<<<<<<< HEAD
            logger.info("Registered master admin bot row (id=%s, @%s)", db_bot.id, me.username)

        # Re-assert webhooks for every active bot on boot -- cheap, and
        # guards against drift after a redeploy or Telegram-side reset.
        await admin_bot.set_webhook(
            url=f"{settings.BASE_WEBHOOK_URL}/webhook/admin",
            secret_token=settings.WEBHOOK_SECRET,
            allowed_updates=["message", "callback_query"],
        )
        child_bots = await repo.list_active_child_bots()
        for db_bot in child_bots:
            bot = await bot_manager.get(db_bot.id)
            if bot is None:
                continue
=======
            logger.info("Registered master admin bot row (id=%s)", db_bot.id)

        # 2. Инициализация всех активных ботов в bot_manager
        child_bots = await repo.list_active_child_bots()
        for db_bot in child_bots:
            # Создаем и добавляем бота в менеджер, чтобы он был доступен
            bot = Bot(token=db_bot.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
            await bot_manager.add(db_bot.id, bot)
            
            # 3. Установка вебхуков
>>>>>>> 4c2f3e7 (fix: resolve Enum/Postgres type errors, fix logger context, fix webhook startup sequence)
            await bot.set_webhook(
                url=f"{settings.BASE_WEBHOOK_URL}/webhook/{db_bot.id}",
                secret_token=settings.WEBHOOK_SECRET,
                allowed_updates=["message", "callback_query", "chat_join_request"],
            )
<<<<<<< HEAD
    logger.info("Startup complete: %d child bot(s) online", len(child_bots))
=======
        
        # Установка вебхука для админа
        await admin_bot.set_webhook(
            url=f"{settings.BASE_WEBHOOK_URL}/webhook/admin",
            secret_token=settings.WEBHOOK_SECRET,
            allowed_updates=["message", "callback_query"],
        )

    logger.info("Startup complete: %d child bot(s) initialized", len(child_bots))
>>>>>>> 4c2f3e7 (fix: resolve Enum/Postgres type errors, fix logger context, fix webhook startup sequence)


async def on_shutdown(app: web.Application) -> None:
    await admin_bot.session.close()
    await bot_manager.close_all()


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/webhook/admin", handle_admin_webhook)
    app.router.add_post("/webhook/{bot_id}", handle_child_webhook)
    app.router.add_get("/health", healthcheck)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app


def main() -> None:
    app = create_app()
    web.run_app(app, host=settings.WEB_SERVER_HOST, port=settings.WEB_SERVER_PORT)


if __name__ == "__main__":
    main()
