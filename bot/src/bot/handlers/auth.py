from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import get_bot_settings
from bot.services.auth import create_auth_token
from bot.services.users import upsert_user
from db.session import session_scope

router = Router(name="auth")


@router.message(Command("auth"))
async def handle_auth(message: Message) -> None:
    if message.from_user is None:
        return

    settings = get_bot_settings()

    async with session_scope() as session:
        user = await upsert_user(
            session,
            telegram_id=message.from_user.id,
            telegram_username=message.from_user.username,
        )
        code = await create_auth_token(
            session, user=user, ttl_minutes=settings.auth_token_ttl_minutes
        )

    await message.answer(
        f"Your login code: {code}\n\n"
        f"It expires in {settings.auth_token_ttl_minutes} minutes.\n\n"
        f"Open the web app and enter this code to log in.\n{settings.app_base_url}"
    )
