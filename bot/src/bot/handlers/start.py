from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.services.users import upsert_user
from db.session import session_scope

router = Router(name="start")

WELCOME_TEXT = (
    "Send me any link and I will save it to your bookmarks.\n\n"
    "You can add tags like #reading #work and notes in the same message.\n\n"
    "Use /auth to log in to the web app."
)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    if message.from_user is None:
        return

    async with session_scope() as session:
        await upsert_user(
            session,
            telegram_id=message.from_user.id,
            telegram_username=message.from_user.username,
        )

    await message.answer(WELCOME_TEXT)
