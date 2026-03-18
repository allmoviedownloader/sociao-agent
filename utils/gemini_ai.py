"""
Gemini AI module - Uses direct REST API (no SDK needed).
No compilation, no grpcio, works on Termux/ARM.
"""
import aiohttp
from bot.config import GEMINI_API_KEY
from utils.logger import logger

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


async def _call_gemini(prompt: str) -> str:
    """Call Gemini API directly via HTTP POST."""
    if not GEMINI_API_KEY:
        return ""

    url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 500,
        },
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    return text.strip()
                else:
                    error = await resp.text()
                    logger.error(f"Gemini API error {resp.status}: {error[:200]}")
                    return ""
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        return ""


async def generate_caption(
    original_username: str,
    original_caption: str = "",
    niche: str = "entertainment",
    style: str = "engaging",
    language: str = "hinglish",
) -> str:
    """Generate an AI-powered caption for a repost."""
    prompt = f"""You are a creative Instagram caption writer. Write a short, viral Instagram reel caption for a REPOST.

RULES:
- MUST credit the original creator: @{original_username}
- Keep it short (3-5 lines max)
- Include relevant emojis
- Language: {language}
- Style: {style}
- Niche: {niche}
- Add 5-8 trending hashtags at the end
- Make it engaging so people like, comment and share
- ALWAYS include "📸 Credits: @{original_username}" as the FIRST line

Original caption context: {original_caption[:200] if original_caption else 'No caption available'}

Write ONLY the caption, nothing else."""

    result = await _call_gemini(prompt)
    if result:
        logger.info(f"🤖 Gemini generated caption for @{original_username}")
        return result

    # Fallback to template
    from utils.helpers import build_credit_caption
    return build_credit_caption(original_username, original_caption)


async def generate_comment(
    post_context: str = "",
    style: str = "supportive",
) -> str:
    """Generate an AI comment for an Instagram post."""
    prompt = f"""Write a short, genuine Instagram comment (1-2 lines max).
Style: {style}
Context: {post_context[:200] if post_context else 'general post'}
- Be natural, not spammy
- Include 1-2 emojis
- Don't use too many hashtags
Write ONLY the comment, nothing else."""

    result = await _call_gemini(prompt)
    return result if result else "Amazing content! 🔥❤️"


async def generate_dm_message(
    recipient_username: str,
    purpose: str = "collaboration",
    context: str = "",
) -> str:
    """Generate an AI direct message for Instagram."""
    prompt = f"""Write a professional but friendly Instagram DM to @{recipient_username}.
Purpose: {purpose}
Context: {context[:200] if context else 'reaching out'}
- Keep it short (3-5 lines)
- Be genuine and respectful
- Don't be too salesy
Write ONLY the message, nothing else."""

    result = await _call_gemini(prompt)
    return result if result else f"Hey @{recipient_username}! Love your content! 🙌"


async def rewrite_caption_custom(
    instruction: str,
    original_text: str = "",
) -> str:
    """Generate any custom text based on user instruction."""
    if not GEMINI_API_KEY:
        return "❌ Gemini API key not configured"

    prompt = f"""Follow this instruction exactly:

{instruction}

{f'Reference text: {original_text[:300]}' if original_text else ''}

Write ONLY the output, nothing else."""

    result = await _call_gemini(prompt)
    return result if result else f"❌ Generation failed"
