from urllib.parse import urlparse

from db.models import AppUser, Bookmark, BookmarkTag, MetadataJob, Tag
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def extract_domain(url: str) -> str | None:
    try:
        netloc = urlparse(url).netloc
    except ValueError:
        return None
    return netloc or None


async def _get_or_create_tags(
    session: AsyncSession, *, user_id: int, tag_names: list[str]
) -> list[Tag]:
    if not tag_names:
        return []

    result = await session.execute(
        select(Tag).where(Tag.user_id == user_id, Tag.tag_name.in_(tag_names))
    )
    existing_by_name = {tag.tag_name: tag for tag in result.scalars().all()}

    tags: list[Tag] = []
    for name in tag_names:
        tag = existing_by_name.get(name)
        if tag is None:
            tag = Tag(user_id=user_id, tag_name=name)
            session.add(tag)
            await session.flush()
            existing_by_name[name] = tag
        tags.append(tag)
    return tags


async def create_bookmark(
    session: AsyncSession,
    *,
    user: AppUser,
    url: str,
    note: str | None,
    tag_names: list[str],
) -> Bookmark:
    """Save a bookmark, its tags, and a pending metadata job in one transaction.

    Per REQUIREMENTS.md §6.4 / §8.2 / §9.1: the bot saves the bookmark and
    enqueues a metadata job immediately; it never fetches metadata itself.
    Duplicate URLs are always allowed (no uniqueness constraint).
    """
    bookmark = Bookmark(
        user_id=user.user_id,
        url=url,
        domain=extract_domain(url),
        note=note,
        metadata_status="pending",
    )
    session.add(bookmark)
    await session.flush()

    tags = await _get_or_create_tags(session, user_id=user.user_id, tag_names=tag_names)
    for tag in tags:
        session.add(BookmarkTag(bookmark_id=bookmark.bookmark_id, tag_id=tag.tag_id))

    session.add(
        MetadataJob(
            bookmark_id=bookmark.bookmark_id,
            user_id=user.user_id,
            url=url,
            status="pending",
        )
    )

    await session.flush()
    return bookmark
