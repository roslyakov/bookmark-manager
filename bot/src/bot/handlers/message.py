from aiogram import F, Router
from aiogram.types import Message

from bot.parsing import parse_message
from bot.services.bookmarks import create_bookmark
from bot.services.users import upsert_user
from db.session import session_scope

router = Router(name="message")

NO_URL_TEXT = "I could not find a link in this message. Please send a URL."

_NOTE_PREVIEW_MAX_LEN = 200


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _format_confirmation(url: str, tags: list[str], note: str | None) -> str:
    lines = ["Saved.", "", url]
    if tags:
        lines.append("")
        lines.append("Tags: " + ", ".join(f"#{t}" for t in tags))
    if note:
        if not tags:
            lines.append("")
        lines.append("Note: " + _truncate(note, _NOTE_PREVIEW_MAX_LEN))
    return "\n".join(lines)


@router.message(F.text)
async def handle_text_message(message: Message) -> None:
    if message.from_user is None or message.text is None:
        return

    parsed = parse_message(message.text)

    if parsed.url is None:
        await message.answer(NO_URL_TEXT)
        return

    async with session_scope() as session:
        user = await upsert_user(
            session,
            telegram_id=message.from_user.id,
            telegram_username=message.from_user.username,
        )
        await create_bookmark(
            session,
            user=user,
            url=parsed.url,
            note=parsed.note,
            tag_names=parsed.tags,
        )

    await message.answer(_format_confirmation(parsed.url, parsed.tags, parsed.note))
