from db.models import AppUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def upsert_user(
    session: AsyncSession, *, telegram_id: int, telegram_username: str | None
) -> AppUser:
    """Create or update the app_user record for this Telegram user.

    Per REQUIREMENTS.md §6.2 / §10.1: identify users by telegram_id, store
    username (optional, may change), never store first/last name.
    """
    result = await session.execute(select(AppUser).where(AppUser.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = AppUser(telegram_id=telegram_id, telegram_username=telegram_username)
        session.add(user)
    elif user.telegram_username != telegram_username:
        user.telegram_username = telegram_username

    await session.flush()
    return user
