"""Telegram bot entrypoint — webhook mode only (REQUIREMENTS.md §6.1).

Long polling is intentionally not used in production. The aiohttp server
listens on an internal port; on the VPS, Traefik terminates TLS and routes
the public TELEGRAM_WEBHOOK_URL to this container.
"""

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from bot.config import get_bot_settings
from bot.handlers import auth, message, start

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    settings = get_bot_settings()
    await bot.set_webhook(
        url=settings.telegram_webhook_url,
        secret_token=settings.telegram_webhook_secret or None,
        drop_pending_updates=False,
    )
    logger.info("Webhook registered: %s", settings.telegram_webhook_url)


async def on_shutdown(bot: Bot) -> None:
    await bot.session.close()


def create_app() -> web.Application:
    settings = get_bot_settings()

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(auth.router)
    dp.include_router(message.router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=settings.telegram_webhook_secret or None,
    )
    webhook_handler.register(app, path=settings.telegram_webhook_path)
    setup_application(app, dp, bot=bot)

    return app


def main() -> None:
    settings = get_bot_settings()
    app = create_app()
    web.run_app(app, host=settings.bot_http_host, port=settings.bot_http_port)


if __name__ == "__main__":
    main()
