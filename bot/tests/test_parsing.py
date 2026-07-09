"""Tests for bot.parsing against REQUIREMENTS.md §6.4-6.5 message rules."""

from bot.parsing import parse_message


def test_plain_url_only():
    result = parse_message("https://example.com/article-about-ai")
    assert result.url == "https://example.com/article-about-ai"
    assert result.tags == []
    assert result.note is None


def test_url_with_note_and_tags_spec_example():
    text = (
        "https://example.com/article-about-ai\n"
        "Interesting article about agents #ai #agents #todo"
    )
    result = parse_message(text)
    assert result.url == "https://example.com/article-about-ai"
    assert result.tags == ["ai", "agents", "todo"]
    assert result.note == "Interesting article about agents"


def test_url_with_surrounding_text():
    text = "Check this out https://example.com/x it's great"
    result = parse_message(text)
    assert result.url == "https://example.com/x"
    assert result.note == "Check this out it's great"


def test_note_before_url():
    text = "Great read on agents https://example.com/agents"
    result = parse_message(text)
    assert result.url == "https://example.com/agents"
    assert result.note == "Great read on agents"


def test_note_after_url():
    text = "https://example.com/agents\nGreat read on agents"
    result = parse_message(text)
    assert result.url == "https://example.com/agents"
    assert result.note == "Great read on agents"


def test_tags_scattered_anywhere_in_message():
    text = "#reading https://example.com/x some text #work more text #later"
    result = parse_message(text)
    assert result.url == "https://example.com/x"
    assert result.tags == ["reading", "work", "later"]
    assert result.note == "some text more text"


def test_multiple_tags():
    text = "https://example.com/x #a #b #c #d"
    result = parse_message(text)
    assert result.tags == ["a", "b", "c", "d"]


def test_no_note_only_url():
    result = parse_message("https://example.com/x")
    assert result.url == "https://example.com/x"
    assert result.note is None


def test_no_tags():
    result = parse_message("https://example.com/x A note without tags")
    assert result.url == "https://example.com/x"
    assert result.tags == []
    assert result.note == "A note without tags"


def test_url_and_no_note_and_no_tags():
    result = parse_message("https://example.com/x")
    assert result.url == "https://example.com/x"
    assert result.tags == []
    assert result.note is None


def test_multiple_urls_saves_first_only():
    text = "https://example.com/first https://example.com/second some note"
    result = parse_message(text)
    assert result.url == "https://example.com/first"


def test_no_url_found():
    result = parse_message("just some text with #tags but no link")
    assert result.url is None


def test_empty_message():
    result = parse_message("")
    assert result.url is None
    assert result.tags == []
    assert result.note is None


def test_tags_are_lowercased_and_deduplicated():
    text = "https://example.com/x #AI #ai #Ai"
    result = parse_message(text)
    assert result.tags == ["ai"]


def test_trailing_punctuation_stripped_from_url():
    text = "Check this out: https://example.com/x/page."
    result = parse_message(text)
    assert result.url == "https://example.com/x/page"


def test_url_fragment_hash_not_treated_as_tag():
    text = "https://example.com/page#section some note #real-tag"
    result = parse_message(text)
    assert result.url == "https://example.com/page#section"
    assert result.tags == ["real"]  # \w+ stops at the hyphen; documents current behavior
    assert "some note" in result.note
