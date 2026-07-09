"""Message parsing: extract URL, hashtags, and note (REQUIREMENTS.md §6.4-6.5).

Rules implemented:
- If multiple URLs are present, only the first is used as the bookmark URL.
- Tags (`#tag`) may appear anywhere in the message; all are collected.
- Whatever text remains after removing the first URL and the tag tokens is
  saved as the note (whitespace-collapsed, trimmed). Empty note -> None.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Matches http(s):// URLs up to the next whitespace character.
_URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)

# Matches #tag tokens; `(?<!\w)` avoids matching mid-word occurrences.
_TAG_RE = re.compile(r"(?<!\w)#(\w+)")

# Trailing punctuation that's commonly not part of the URL itself
# (e.g. "check this out: https://example.com/x." -> trailing period).
_URL_TRAILING_PUNCTUATION = ".,;:!?)]}\'\""


@dataclass
class ParsedMessage:
    url: str | None
    tags: list[str] = field(default_factory=list)
    note: str | None = None


def _clean_url(raw: str) -> str:
    return raw.rstrip(_URL_TRAILING_PUNCTUATION)


def parse_message(text: str) -> ParsedMessage:
    if not text:
        return ParsedMessage(url=None, tags=[], note=None)

    url_matches = list(_URL_RE.finditer(text))
    first_url_match = url_matches[0] if url_matches else None

    remove_spans: list[tuple[int, int]] = []
    url: str | None = None
    url_full_span: tuple[int, int] | None = None

    if first_url_match:
        url_full_span = first_url_match.span()
        url = _clean_url(first_url_match.group(0))
        # Only remove the cleaned portion from the note text; trailing
        # punctuation (if any) is left for the note remainder.
        cleaned_end = url_full_span[0] + len(url)
        remove_spans.append((url_full_span[0], cleaned_end))

    tags_ordered: list[str] = []
    seen: set[str] = set()
    for m in _TAG_RE.finditer(text):
        # Skip hashtag-looking matches that are actually inside the URL
        # (e.g. a URL fragment like https://example.com/page#section).
        if url_full_span and url_full_span[0] <= m.start() < url_full_span[1]:
            continue
        name = m.group(1).lower()
        remove_spans.append(m.span())
        if name and name not in seen:
            seen.add(name)
            tags_ordered.append(name)

    remove_spans.sort()
    note_parts: list[str] = []
    cursor = 0
    for start, end in remove_spans:
        if start > cursor:
            note_parts.append(text[cursor:start])
        cursor = max(cursor, end)
    note_parts.append(text[cursor:])
    remainder = "".join(note_parts)

    # Collapse runs of spaces/tabs left behind by removed tokens (e.g. a tag
    # surrounded by spaces on both sides leaves a double space once cut out),
    # then join non-empty lines with a single space.
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in remainder.splitlines()]
    note = " ".join(line for line in lines if line).strip()

    return ParsedMessage(url=url, tags=tags_ordered, note=note or None)
