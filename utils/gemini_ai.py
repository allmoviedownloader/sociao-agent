"""
Gemini AI module - Uses direct REST API (no SDK needed).
No compilation, no grpcio, works on Termux/ARM.
Includes rate limit handling and automatic cooldown.
"""
import time
import asyncio
import aiohttp
from bot.config import GEMINI_API_KEY
from utils.logger import logger

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Rate limiting — track when we last hit a 429
_last_429_time = 0
_cooldown_seconds = 60  # Wait 60 seconds after hitting 429


def _is_on_cooldown() -> bool:
    """Check if we should skip API calls due to recent 429 error."""
    global _last_429_time
    if _last_429_time == 0:
        return False
    elapsed = time.time() - _last_429_time
    return elapsed < _cooldown_seconds


async def _call_gemini(prompt: str) -> str:
    """Call Gemini API directly via HTTP POST with rate limit handling."""
    global _last_429_time

    if not GEMINI_API_KEY:
        return ""

    # If we recently hit a 429, don't spam the API
    if _is_on_cooldown():
        remaining = int(_cooldown_seconds - (time.time() - _last_429_time))
        logger.warning(f"⏳ Gemini on cooldown, {remaining}s remaining")
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
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Reset cooldown on success
                    _last_429_time = 0
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    return text.strip()
                elif resp.status == 429:
                    # Rate limited — set cooldown
                    _last_429_time = time.time()
                    logger.warning("⚠️ Gemini API quota exceeded, cooling down 60s...")
                    return ""
                else:
                    error = await resp.text()
                    logger.error(f"Gemini API error {resp.status}: {error[:200]}")
                    return ""
    except asyncio.TimeoutError:
        logger.error("Gemini API timeout (30s)")
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
    return result if result else "❌ Generation failed"


async def chat_with_ai(user_message: str, context: str = "") -> str:
    """
    Full conversational AI - acts as personal assistant + Instagram growth expert.
    Responds to any message like a normal AI chatbot.
    """
    system_prompt = """You are SOCIO — a smart, friendly AI assistant that lives inside Telegram. You are the user's personal companion AND Instagram growth expert.

YOUR PERSONALITY:
- Talk in Hinglish (mix of Hindi + English), casual and friendly
- Be helpful, encouraging, and supportive
- Use emojis naturally 😊🔥💪
- Be honest about what you know and don't know
- You can discuss daily life, technology, business, motivation, or ANYTHING

YOUR EXPERTISE:
- Instagram growth strategies and algorithms
- Content creation and viral hooks
- Trending topics and hashtag research
- Engagement optimization (best posting times, caption styles)
- Reels strategies (what types of content get more views)
- Competitor analysis
- Building an audience from zero

WHEN ASKED ABOUT INSTAGRAM/CONTENT:
- Give specific, actionable advice
- Mention current trends
- Suggest content calendar ideas
- Explain Instagram algorithm tips
- Help with caption writing, hashtag selection
- Analyze what's working and what's not

REMEMBER: You ARE the agent. The user controls you via Telegram. You manage their Instagram repost accounts (@the.unscrptd and @tobex.96)."""

    prompt = f"""{system_prompt}

{f'Recent context: {context}' if context else ''}

User says: {user_message}

Reply naturally (keep it concise, 2-10 lines max):"""

    result = await _call_gemini(prompt)
    if result:
        return result

    # Friendly fallback when API is down or rate limited
    if _is_on_cooldown():
        return "🙏 Bhai abhi API thoda rest le raha hai (quota limit). 1 minute mein try kar phir se!"
    return "Bhai sorry, thoda issue aa gaya. Phir se try kar! 🙏"


async def research_trending(niche: str = "entertainment") -> str:
    """Research trending topics, hooks, and content ideas."""
    prompt = f"""You are an Instagram Reels expert. Research and give me:

NICHE: {niche}

1. 🔥 Top 5 TRENDING topics right now for Reels in this niche
2. 🎣 5 Viral HOOKS (first 3 seconds ideas) that get maximum views
3. ⏰ Best posting times (IST) for maximum reach
4. #️⃣ Top 10 trending hashtags for this niche right now
5. 💡 3 Content ideas that are GUARANTEED to get views

Be specific with actual examples and trends. Format nicely with emojis.
Keep it actionable and practical. Output in Hinglish."""

    result = await _call_gemini(prompt)
    if result:
        return result
    if _is_on_cooldown():
        return "⏳ API quota limit hit. 1 minute baad try karo!"
    return "❌ Research failed. Try again!"


async def create_strategy(goal: str = "grow followers", days: int = 7) -> str:
    """Create a complete Instagram growth strategy."""
    prompt = f"""You are a top Instagram growth strategist. Create a detailed {days}-day action plan.

GOAL: {goal}
ACCOUNTS: @the.unscrptd and @tobex.96
CONTENT: Reposted viral reels with credit

Create a day-by-day plan including:
- 📅 What to post each day (type, niche, timing)
- 📊 How many posts per day
- #️⃣ Hashtag strategy for each day
- 🎯 Engagement tactics (commenting, following, etc.)
- 📈 Expected growth metrics
- 💡 Pro tips for each day

Make it realistic and actionable. Format with emojis. Output in Hinglish.
Keep each day's plan concise (3-4 lines max per day)."""

    result = await _call_gemini(prompt)
    if result:
        return result
    if _is_on_cooldown():
        return "⏳ API quota limit hit. 1 minute baad try karo!"
    return "❌ Strategy creation failed. Try again!"
