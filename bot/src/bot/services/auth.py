import datetime as dt
import hashlib
import secrets

from db.models import AppUser, AuthToken
from sqlalchemy.ext.asyncio import AsyncSession


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _generate_code() -> str:
    """Cryptographically secure 6-digit numeric login code (e.g. "042317")."""
    return f"{secrets.randbelow(1_000_000):06d}"


async def create_auth_token(
    session: AsyncSession, *, user: AppUser, ttl_minutes: int
) -> str:
    """Create a short-lived, single-use login code for `user`.

    Only the SHA-256 hash is persisted (REQUIREMENTS.md §6.3 / §10.5). The
    raw code is returned so the caller can send it to the user once; it is
    never stored or logged.
    """
    raw_token = _generate_code()
    now = dt.datetime.now(dt.timezone.utc)
    auth_token = AuthToken(
        user_id=user.user_id,
        token_hash=_hash_token(raw_token),
        expires_at=now + dt.timedelta(minutes=ttl_minutes),
    )
    session.add(auth_token)
    await session.flush()
    return raw_token
