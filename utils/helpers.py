"""
Helper utilities - Caption builder, mention formatter, etc.
"""
from bot.config import CREDIT_TEMPLATE, DEFAULT_HASHTAGS


def build_credit_caption(
    original_username: str,
    original_caption: str = "",
    custom_hashtags: list[str] | None = None,
) -> str:
    """
    Build a repost caption with proper credit to the original creator.

    Args:
        original_username: The original creator's Instagram username.
        original_caption: Snippet of the original caption (truncated).
        custom_hashtags: Optional list of hashtags to use instead of defaults.
    """
    # Truncate original caption if too long
    caption_snippet = ""
    if original_caption:
        clean = original_caption.strip().replace("\n", " ")
        caption_snippet = clean[:150] + "..." if len(clean) > 150 else clean

    hashtags = " ".join(custom_hashtags or DEFAULT_HASHTAGS)

    caption = CREDIT_TEMPLATE.format(
        original_username=original_username,
        caption_snippet=caption_snippet,
        hashtags=hashtags,
    )
    return caption.strip()


def sanitize_filename(name: str) -> str:
    """Remove special characters from filename."""
    import re
    return re.sub(r'[^\w\-.]', '_', name)


def format_number(n: int) -> str:
    """Format large numbers: 1500 -> 1.5K, 1500000 -> 1.5M"""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def truncate_text(text: str, max_len: int = 100) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
