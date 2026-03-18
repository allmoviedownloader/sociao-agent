"""
Telegram Bot - Full command handler for controlling the Instagram Repost Agent.
"""
import asyncio
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.enums import ParseMode

from bot.config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_ID, MAX_POSTS_PER_DAY,
    IG_ACCOUNTS, SCRAPE_INTERVAL_HOURS, POST_INTERVAL_MINUTES,
)
from database import db
from utils.logger import logger, get_recent_logs
from utils.helpers import format_number, truncate_text

# Router for handling commands
router = Router()


def is_admin(message: Message) -> bool:
    """Check if message is from the admin."""
    return message.from_user and message.from_user.id == TELEGRAM_ADMIN_ID


# ═══════════════════════════════════════
#  /start - Bot Introduction
# ═══════════════════════════════════════
@router.message(CommandStart())
async def cmd_start(message: Message):
    if not is_admin(message):
        return await message.answer("⛔ Unauthorized. This bot is private.")

    text = """
🤖 *Instagram Repost Agent* — Ready!

━━━━━━━━━━━━━━━━━━━━━━━━━

📋 *Available Commands:*

🔍 *Scraping:*
/scrape — Scrape trending reels (explore)
/scrape\\_hashtag `<tag>` — Scrape from hashtag
/scrape\\_user `<username>` — Scrape from user
/scrape\\_targets — Scrape all target accounts

🎯 *Targets:*
/add\\_target `<username>` — Add target
/remove\\_target `<username>` — Remove target
/targets — Show all targets

📤 *Posting:*
/post — Post next reel from queue
/postall — Auto-post all queued reels
/queue — View pending queue

⏰ *Scheduling:*
/daily `9:00,14:00,20:00` — Set daily post times
/daily\\_off — Stop daily schedule
/daily\\_status — Show active schedule
/schedule\\_on — Start interval mode
/schedule\\_off — Stop interval mode
/set\\_interval `<min>` — Post interval
/set\\_scrape `<hrs>` — Scrape interval

🤖 *AI (Gemini):*
/ai\\_caption `<user> [niche]` — Generate AI caption
/ai\\_comment `[context]` — Generate comment
/ai\\_dm `<user> [purpose]` — Generate DM
/ai\\_ask `<question>` — Ask Gemini anything

📊 *Info:*
/status — Current status
/stats — Overall statistics
/logs — Recent activity logs

🔧 *Control:*
/switch `<1|2>` — Switch IG account
/set\\_maxposts `<N>` — Set daily limit
/help — Show this message

━━━━━━━━━━━━━━━━━━━━━━━━━
Active: @{active} | Limit: {limit}/day
""".format(
        active=IG_ACCOUNTS[0]["username"],
        limit=MAX_POSTS_PER_DAY,
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════
#  /help - Same as start
# ═══════════════════════════════════════
@router.message(Command("help"))
async def cmd_help(message: Message):
    if not is_admin(message):
        return
    await cmd_start(message)


# ═══════════════════════════════════════
#  /status - Current Status
# ═══════════════════════════════════════
@router.message(Command("status"))
async def cmd_status(message: Message):
    if not is_admin(message):
        return

    from scheduler.jobs import is_scheduler_running

    stats = await db.get_stats()
    scheduler_status = "🟢 Running" if is_scheduler_running() else "🔴 Stopped"

    text = f"""
📊 *Agent Status*
━━━━━━━━━━━━━━━━━━
🤖 Scheduler: {scheduler_status}
📅 Today Posts: {stats['today_posts']}/{MAX_POSTS_PER_DAY}
📥 Queue: {stats['queue_size']} reels
✅ Total Posted: {stats['total_posted']}
🔍 Total Scraped: {stats['total_scraped']}
❌ Total Failed: {stats['total_failed']}
━━━━━━━━━━━━━━━━━━
👤 Account 1: @{IG_ACCOUNTS[0]['username']}
👤 Account 2: @{IG_ACCOUNTS[1]['username']}
"""
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════
#  /stats - Overall Statistics
# ═══════════════════════════════════════
@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if not is_admin(message):
        return

    stats = await db.get_stats()
    text = f"""
📈 *Overall Statistics*
━━━━━━━━━━━━━━━━━━
🔍 Total Scraped: {format_number(stats['total_scraped'])}
✅ Total Posted: {format_number(stats['total_posted'])}
❌ Total Failed: {format_number(stats['total_failed'])}
📥 Current Queue: {stats['queue_size']}
📅 Posted Today: {stats['today_posts']}/{MAX_POSTS_PER_DAY}
"""
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════
#  /scrape - Scrape Explore Page
# ═══════════════════════════════════════
@router.message(Command("scrape"))
async def cmd_scrape(message: Message):
    if not is_admin(message):
        return

    await message.answer("🔍 Scraping trending reels from Explore page...")

    from instagram.scraper import InstagramScraper

    try:
        scraper = InstagramScraper()
        added = await scraper.scrape_and_queue(mode="explore", count=20)
        await message.answer(f"✅ Done! {added} new reels added to queue")
    except Exception as e:
        await message.answer(f"❌ Scrape failed: {str(e)[:200]}")


# ═══════════════════════════════════════
#  /scrape_hashtag - Scrape by Hashtag
# ═══════════════════════════════════════
@router.message(Command("scrape_hashtag"))
async def cmd_scrape_hashtag(message: Message):
    if not is_admin(message):
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("Usage: /scrape\\_hashtag `<hashtag>`\nExample: /scrape\\_hashtag trending",
                                     parse_mode=ParseMode.MARKDOWN)

    hashtag = args[1].strip().lstrip("#")
    await message.answer(f"🔍 Scraping reels from #{hashtag}...")

    from instagram.scraper import InstagramScraper

    try:
        scraper = InstagramScraper()
        added = await scraper.scrape_and_queue(mode="hashtag", hashtag=hashtag, count=20)
        await message.answer(f"✅ Done! {added} new reels from #{hashtag} added to queue")
    except Exception as e:
        await message.answer(f"❌ Scrape failed: {str(e)[:200]}")


# ═══════════════════════════════════════
#  /scrape_user - Scrape from User
# ═══════════════════════════════════════
@router.message(Command("scrape_user"))
async def cmd_scrape_user(message: Message):
    if not is_admin(message):
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("Usage: /scrape\\_user `<username>`\nExample: /scrape\\_user viratkholi",
                                     parse_mode=ParseMode.MARKDOWN)

    username = args[1].strip().lstrip("@")
    await message.answer(f"🔍 Scraping reels from @{username}...")

    from instagram.scraper import InstagramScraper

    try:
        scraper = InstagramScraper()
        added = await scraper.scrape_and_queue(mode="user", username=username, count=15)
        await message.answer(f"✅ Done! {added} new reels from @{username} added to queue")
    except Exception as e:
        await message.answer(f"❌ Scrape failed: {str(e)[:200]}")


# ═══════════════════════════════════════
#  /scrape_targets - Scrape All Targets
# ═══════════════════════════════════════
@router.message(Command("scrape_targets"))
async def cmd_scrape_targets(message: Message):
    if not is_admin(message):
        return

    targets = await db.get_target_accounts()
    if not targets:
        return await message.answer("⚠️ No target accounts set. Use /add\\_target to add some.",
                                     parse_mode=ParseMode.MARKDOWN)

    await message.answer(f"🎯 Scraping {len(targets)} target accounts...")

    from instagram.scraper import InstagramScraper

    try:
        scraper = InstagramScraper()
        added = await scraper.scrape_and_queue(mode="targets", count=5)
        await message.answer(f"✅ Done! {added} new reels from target accounts added to queue")
    except Exception as e:
        await message.answer(f"❌ Scrape failed: {str(e)[:200]}")


# ═══════════════════════════════════════
#  /add_target & /remove_target
# ═══════════════════════════════════════
@router.message(Command("add_target"))
async def cmd_add_target(message: Message):
    if not is_admin(message):
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("Usage: /add\\_target `<username>`",
                                     parse_mode=ParseMode.MARKDOWN)

    username = args[1].strip().lstrip("@")
    await db.add_target_account(username)
    await message.answer(f"✅ Added @{username} to target accounts")


@router.message(Command("remove_target"))
async def cmd_remove_target(message: Message):
    if not is_admin(message):
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("Usage: /remove\\_target `<username>`",
                                     parse_mode=ParseMode.MARKDOWN)

    username = args[1].strip().lstrip("@")
    await db.remove_target_account(username)
    await message.answer(f"✅ Removed @{username} from target accounts")


@router.message(Command("targets"))
async def cmd_targets(message: Message):
    if not is_admin(message):
        return

    targets = await db.get_target_accounts()
    if not targets:
        return await message.answer("📭 No target accounts set.\nUse /add\\_target `<username>` to add.",
                                     parse_mode=ParseMode.MARKDOWN)

    text = "🎯 *Target Accounts:*\n━━━━━━━━━━━━━━━━━━\n"
    for i, t in enumerate(targets, 1):
        text += f"{i}. @{t}\n"
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════
#  /queue - View Queue
# ═══════════════════════════════════════
@router.message(Command("queue"))
async def cmd_queue(message: Message):
    if not is_admin(message):
        return

    items = await db.get_queue_list(limit=10)
    total = await db.get_queue_count()

    if not items:
        return await message.answer("📭 Queue is empty!\nUse /scrape to find reels.")

    text = f"📥 *Post Queue* ({total} total)\n━━━━━━━━━━━━━━━━━━\n"
    for i, item in enumerate(items, 1):
        caption_preview = truncate_text(item.get("caption", ""), 50)
        text += f"{i}. @{item['username']} — {caption_preview}\n"

    if total > 10:
        text += f"\n_...and {total - 10} more_"

    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════
#  /post - Post Next Reel
# ═══════════════════════════════════════
@router.message(Command("post"))
async def cmd_post(message: Message):
    if not is_admin(message):
        return

    today_count = await db.get_today_post_count()
    if today_count >= MAX_POSTS_PER_DAY:
        return await message.answer(
            f"⚠️ Daily limit reached ({today_count}/{MAX_POSTS_PER_DAY}).\n"
            f"Use /set\\_maxposts to change limit.",
            parse_mode=ParseMode.MARKDOWN,
        )

    await message.answer("📤 Posting next reel from queue...")

    from instagram.uploader import InstagramUploader

    try:
        uploader = InstagramUploader()
        result = await uploader.post_next_from_queue()

        if result:
            await message.answer(
                f"✅ *Posted Successfully!*\n"
                f"📸 Credit: @{result['username']}\n"
                f"📊 Today: {today_count + 1}/{MAX_POSTS_PER_DAY}",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await message.answer("❌ Could not post. Queue might be empty or daily limit reached.")
    except Exception as e:
        await message.answer(f"❌ Post failed: {str(e)[:200]}")


# ═══════════════════════════════════════
#  /postall - Post All Queued Reels
# ═══════════════════════════════════════
@router.message(Command("postall"))
async def cmd_postall(message: Message):
    if not is_admin(message):
        return

    from instagram.uploader import InstagramUploader
    from bot.config import MIN_DELAY_BETWEEN_POSTS_SECONDS

    queue_count = await db.get_queue_count()
    today_count = await db.get_today_post_count()
    remaining = MAX_POSTS_PER_DAY - today_count
    to_post = min(queue_count, remaining)

    if to_post <= 0:
        return await message.answer("⚠️ Nothing to post (queue empty or daily limit reached)")

    await message.answer(
        f"📤 Starting to post {to_post} reels...\n"
        f"⏱️ Interval: {MIN_DELAY_BETWEEN_POSTS_SECONDS}s between posts"
    )

    uploader = InstagramUploader()
    success_count = 0

    for i in range(to_post):
        result = await uploader.post_next_from_queue()
        if result:
            success_count += 1
            await message.answer(
                f"✅ [{success_count}/{to_post}] Posted @{result['username']}"
            )
        else:
            await message.answer(f"❌ [{i+1}/{to_post}] Failed or queue empty")
            break

        # Wait between posts
        if i < to_post - 1:
            await asyncio.sleep(MIN_DELAY_BETWEEN_POSTS_SECONDS)

    await message.answer(
        f"🏁 *Post All Complete!*\n"
        f"✅ Posted: {success_count}/{to_post}",
        parse_mode=ParseMode.MARKDOWN,
    )


# ═══════════════════════════════════════
#  /schedule_on & /schedule_off
# ═══════════════════════════════════════
@router.message(Command("schedule_on"))
async def cmd_schedule_on(message: Message):
    if not is_admin(message):
        return

    from scheduler.jobs import start_scheduler, is_scheduler_running, set_notifier

    if is_scheduler_running():
        return await message.answer("⏰ Scheduler is already running!")

    # Set up notification callback
    bot = message.bot
    async def send_notification(text: str):
        await bot.send_message(TELEGRAM_ADMIN_ID, text)

    set_notifier(send_notification)
    start_scheduler()

    await message.answer(
        f"⏰ *Scheduler Started!*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔍 Auto-scrape: every {SCRAPE_INTERVAL_HOURS}h\n"
        f"📤 Auto-post: every {POST_INTERVAL_MINUTES}min\n"
        f"🧹 Cleanup: daily at 3 AM\n"
        f"💓 Health check: every 12h\n\n"
        f"Use /schedule\\_off to stop.",
        parse_mode=ParseMode.MARKDOWN,
    )


@router.message(Command("schedule_off"))
async def cmd_schedule_off(message: Message):
    if not is_admin(message):
        return

    from scheduler.jobs import stop_scheduler, is_scheduler_running

    if not is_scheduler_running():
        return await message.answer("⏰ Scheduler is not running.")

    stop_scheduler()
    await message.answer("⏰ Scheduler stopped. No more auto scraping/posting.")


# ═══════════════════════════════════════
#  /set_interval & /set_scrape
# ═══════════════════════════════════════
@router.message(Command("set_interval"))
async def cmd_set_interval(message: Message):
    if not is_admin(message):
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip().isdigit():
        return await message.answer("Usage: /set\\_interval `<minutes>`\nExample: /set\\_interval 45",
                                     parse_mode=ParseMode.MARKDOWN)

    minutes = int(args[1].strip())
    if minutes < 5:
        return await message.answer("⚠️ Minimum interval is 5 minutes")

    from scheduler.jobs import update_post_interval, is_scheduler_running

    if is_scheduler_running():
        update_post_interval(minutes)
        await message.answer(f"✅ Post interval updated to {minutes} minutes")
    else:
        await message.answer("⚠️ Scheduler not running. Start with /schedule\\_on first.",
                             parse_mode=ParseMode.MARKDOWN)


@router.message(Command("set_scrape"))
async def cmd_set_scrape(message: Message):
    if not is_admin(message):
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip().isdigit():
        return await message.answer("Usage: /set\\_scrape `<hours>`\nExample: /set\\_scrape 6",
                                     parse_mode=ParseMode.MARKDOWN)

    hours = int(args[1].strip())
    if hours < 1:
        return await message.answer("⚠️ Minimum interval is 1 hour")

    from scheduler.jobs import update_scrape_interval, is_scheduler_running

    if is_scheduler_running():
        update_scrape_interval(hours)
        await message.answer(f"✅ Scrape interval updated to {hours} hours")
    else:
        await message.answer("⚠️ Scheduler not running. Start with /schedule\\_on first.",
                             parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════
#  /set_maxposts - Change Daily Limit
# ═══════════════════════════════════════
@router.message(Command("set_maxposts"))
async def cmd_set_maxposts(message: Message):
    if not is_admin(message):
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip().isdigit():
        return await message.answer("Usage: /set\\_maxposts `<number>`\nExample: /set\\_maxposts 15",
                                     parse_mode=ParseMode.MARKDOWN)

    import bot.config as config
    new_limit = int(args[1].strip())
    if new_limit < 1 or new_limit > 25:
        return await message.answer("⚠️ Limit must be between 1 and 25 (Instagram max)")

    config.MAX_POSTS_PER_DAY = new_limit
    await message.answer(f"✅ Daily post limit updated to {new_limit}")


# ═══════════════════════════════════════
#  /switch - Switch Active IG Account
# ═══════════════════════════════════════
@router.message(Command("switch"))
async def cmd_switch(message: Message):
    if not is_admin(message):
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2 or args[1].strip() not in ("1", "2"):
        return await message.answer(
            f"Usage: /switch `<1|2>`\n"
            f"1 = @{IG_ACCOUNTS[0]['username']}\n"
            f"2 = @{IG_ACCOUNTS[1]['username']}",
            parse_mode=ParseMode.MARKDOWN,
        )

    import bot.config as config
    idx = int(args[1].strip()) - 1
    config.DEFAULT_ACTIVE_ACCOUNT = idx
    await message.answer(f"✅ Switched to account: @{IG_ACCOUNTS[idx]['username']}")


# ═══════════════════════════════════════
#  /logs - Recent Activity Logs
# ═══════════════════════════════════════
@router.message(Command("logs"))
async def cmd_logs(message: Message):
    if not is_admin(message):
        return

    logs = get_recent_logs(15)
    if len(logs) > 4000:
        logs = logs[-4000:]

    await message.answer(f"📋 *Recent Logs:*\n```\n{logs}\n```", parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════
#  /ai_caption - Generate AI Caption
# ═══════════════════════════════════════
@router.message(Command("ai_caption"))
async def cmd_ai_caption(message: Message):
    if not is_admin(message):
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer(
            "Usage: /ai\\_caption `<username> [niche]`\n"
            "Example: /ai\\_caption viratkholi fitness",
            parse_mode=ParseMode.MARKDOWN,
        )

    parts = args[1].strip().split()
    username = parts[0].lstrip("@")
    niche = parts[1] if len(parts) > 1 else "entertainment"

    await message.answer("🤖 Generating AI caption...")

    from utils.gemini_ai import generate_caption

    caption = await generate_caption(original_username=username, niche=niche)
    await message.answer(f"📝 *Generated Caption:*\n\n{caption}", parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════
#  /ai_comment - Generate AI Comment
# ═══════════════════════════════════════
@router.message(Command("ai_comment"))
async def cmd_ai_comment(message: Message):
    if not is_admin(message):
        return

    args = message.text.split(maxsplit=1)
    context = args[1].strip() if len(args) > 1 else ""

    await message.answer("🤖 Generating comment...")

    from utils.gemini_ai import generate_comment

    comment = await generate_comment(post_context=context)
    await message.answer(f"💬 *Generated Comment:*\n\n{comment}", parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════
#  /ai_dm - Generate AI DM Message
# ═══════════════════════════════════════
@router.message(Command("ai_dm"))
async def cmd_ai_dm(message: Message):
    if not is_admin(message):
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer(
            "Usage: /ai\\_dm `<username> [purpose]`\n"
            "Example: /ai\\_dm viratkholi collaboration",
            parse_mode=ParseMode.MARKDOWN,
        )

    parts = args[1].strip().split(maxsplit=1)
    username = parts[0].lstrip("@")
    purpose = parts[1] if len(parts) > 1 else "collaboration"

    await message.answer("🤖 Generating DM...")

    from utils.gemini_ai import generate_dm_message

    dm = await generate_dm_message(recipient_username=username, purpose=purpose)
    await message.answer(f"✉️ *Generated DM:*\n\n{dm}", parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════
#  /ai_ask - Ask Gemini Anything
# ═══════════════════════════════════════
@router.message(Command("ai_ask"))
async def cmd_ai_ask(message: Message):
    if not is_admin(message):
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("Usage: /ai\\_ask `<your question>`",
                                     parse_mode=ParseMode.MARKDOWN)

    await message.answer("🤖 Thinking...")

    from utils.gemini_ai import rewrite_caption_custom

    result = await rewrite_caption_custom(instruction=args[1].strip())
    # Truncate if too long for Telegram
    if len(result) > 4000:
        result = result[:4000] + "..."
    await message.answer(result)


# ═══════════════════════════════════════
#  /daily - Set Fixed Daily Post Times
# ═══════════════════════════════════════
@router.message(Command("daily"))
async def cmd_daily(message: Message):
    """Set specific times for daily auto-posting.
    Example: /daily 9:00,14:00,20:00
    This will post one reel at 9 AM, 2 PM, and 8 PM every day.
    """
    if not is_admin(message):
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer(
            "Usage: /daily `<times>`\n"
            "Example: /daily 9:00,14:00,20:00\n\n"
            "This will auto\\-scrape \\+ post 1 reel at each given time daily\\.\n"
            "Use /daily\\_off to stop\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )

    times_str = args[1].strip()
    time_slots = []

    for t in times_str.split(","):
        t = t.strip()
        try:
            parts = t.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                time_slots.append((hour, minute))
            else:
                return await message.answer(f"❌ Invalid time: {t}")
        except (ValueError, IndexError):
            return await message.answer(f"❌ Invalid time format: {t}\nUse HH:MM format")

    if not time_slots:
        return await message.answer("❌ No valid times provided")

    # Set up notification callback
    bot = message.bot
    async def send_notification(text: str):
        await bot.send_message(TELEGRAM_ADMIN_ID, text)

    from scheduler.jobs import scheduler, set_notifier, auto_scrape_job, auto_post_job
    from apscheduler.triggers.cron import CronTrigger

    set_notifier(send_notification)

    # Remove any existing daily jobs
    for job in scheduler.get_jobs():
        if job.id.startswith("daily_post_") or job.id == "daily_scrape":
            scheduler.remove_job(job.id)

    if not scheduler.running:
        scheduler.start()

    # Add a scrape job 30 min before first post time
    first_hour, first_min = time_slots[0]
    scrape_min = first_min - 30
    scrape_hour = first_hour
    if scrape_min < 0:
        scrape_min += 60
        scrape_hour -= 1
        if scrape_hour < 0:
            scrape_hour = 23

    scheduler.add_job(
        auto_scrape_job,
        CronTrigger(hour=scrape_hour, minute=scrape_min),
        id="daily_scrape",
        replace_existing=True,
        name="Daily Scrape",
    )

    # Add a post job for each time
    for i, (hour, minute) in enumerate(time_slots):
        scheduler.add_job(
            auto_post_job,
            CronTrigger(hour=hour, minute=minute),
            id=f"daily_post_{i}",
            replace_existing=True,
            name=f"Daily Post {hour:02d}:{minute:02d}",
        )

    times_display = ", ".join(f"{h:02d}:{m:02d}" for h, m in time_slots)
    await message.answer(
        f"⏰ *Daily Schedule Set!*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📤 Post times: {times_display}\n"
        f"🔍 Auto-scrape: {scrape_hour:02d}:{scrape_min:02d}\n"
        f"📊 Max posts/day: {MAX_POSTS_PER_DAY}\n\n"
        f"Agent will now auto\\-post at these times daily\\.\n"
        f"Use /daily\\_off to stop\\.",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    logger.info(f"⏰ Daily schedule set: {times_display}")


# ═══════════════════════════════════════
#  /daily_off - Stop Daily Schedule
# ═══════════════════════════════════════
@router.message(Command("daily_off"))
async def cmd_daily_off(message: Message):
    if not is_admin(message):
        return

    from scheduler.jobs import scheduler

    removed = 0
    for job in scheduler.get_jobs():
        if job.id.startswith("daily_post_") or job.id == "daily_scrape":
            scheduler.remove_job(job.id)
            removed += 1

    if removed:
        await message.answer(f"⏰ Daily schedule stopped. Removed {removed} scheduled jobs.")
    else:
        await message.answer("⏰ No daily schedule was active.")

    logger.info("⏰ Daily schedule stopped")


# ═══════════════════════════════════════
#  /daily_status - Show Daily Schedule
# ═══════════════════════════════════════
@router.message(Command("daily_status"))
async def cmd_daily_status(message: Message):
    if not is_admin(message):
        return

    from scheduler.jobs import scheduler

    daily_jobs = [j for j in scheduler.get_jobs()
                  if j.id.startswith("daily_post_") or j.id == "daily_scrape"]

    if not daily_jobs:
        return await message.answer("📭 No daily schedule active.\nUse /daily to set one.")

    text = "⏰ *Active Daily Schedule:*\n━━━━━━━━━━━━━━━━━━\n"
    for job in daily_jobs:
        next_run = job.next_run_time.strftime("%H:%M") if job.next_run_time else "?"
        text += f"• {job.name} → Next: {next_run}\n"

    await message.answer(text, parse_mode=ParseMode.MARKDOWN)



# ═══════════════════════════════════════
#  /update - Pull from GitHub & Restart
# ═══════════════════════════════════════
@router.message(Command('update'))
async def cmd_update(message: Message):
    if not is_admin(message):
        return

    await message.answer('�� Pulling latest code from GitHub...')

    import subprocess
    import sys
    import os

    try:
        cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            ['git', 'pull', 'origin', 'main'],
            capture_output=True, text=True, cwd=cwd,
            timeout=30,
        )

        if result.returncode == 0:
            output = result.stdout.strip()
            if 'Already up to date' in output:
                await message.answer('✅ Already up to date! No changes.')
                return

            await message.answer(
                f'✅ Code updated!\n{output[:500]}\n\n🔄 Restarting bot in 2 seconds...',
            )
            await asyncio.sleep(2)
            os.execv(sys.executable, [sys.executable, '-m', 'bot.main'])
        else:
            error = result.stderr.strip()
            await message.answer(f'❌ Git pull failed:\n{error[:500]}')
    except Exception as e:
        await message.answer(f'❌ Update failed: {str(e)[:200]}')


# ═══════════════════════════════════════
#  /strategy - AI Growth Strategy
# ═══════════════════════════════════════
@router.message(Command('strategy'))
async def cmd_strategy(message: Message):
    if not is_admin(message):
        return

    args = message.text.split(maxsplit=1)
    goal = args[1].strip() if len(args) > 1 else 'grow followers fast'

    await message.answer('🧠 Creating your growth strategy...')

    from utils.gemini_ai import create_strategy

    result = await create_strategy(goal=goal)
    if len(result) > 4000:
        for i in range(0, len(result), 4000):
            await message.answer(result[i:i+4000])
    else:
        await message.answer(result)


# ═══════════════════════════════════════
#  /research - Trending Topics Research
# ═══════════════════════════════════════
@router.message(Command('research'))
async def cmd_research(message: Message):
    if not is_admin(message):
        return

    args = message.text.split(maxsplit=1)
    niche = args[1].strip() if len(args) > 1 else 'entertainment'

    await message.answer(f'🔍 Researching trending topics in {niche}...')

    from utils.gemini_ai import research_trending

    result = await research_trending(niche=niche)
    if len(result) > 4000:
        for i in range(0, len(result), 4000):
            await message.answer(result[i:i+4000])
    else:
        await message.answer(result)


# ═══════════════════════════════════════
#  CONVERSATIONAL AI - Catch All Messages
#  (MUST be LAST handler - catches everything)
# ═══════════════════════════════════════
@router.message(F.text)
async def chat_handler(message: Message):
    if not is_admin(message):
        return await message.answer('⛔ Unauthorized.')

    user_text = message.text.strip()
    if not user_text or user_text.startswith('/'):
        return

    from aiogram.enums import ChatAction
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    from utils.gemini_ai import chat_with_ai

    reply = await chat_with_ai(user_message=user_text)

    if len(reply) > 4000:
        for i in range(0, len(reply), 4000):
            await message.answer(reply[i:i+4000])
    else:
        await message.answer(reply)
