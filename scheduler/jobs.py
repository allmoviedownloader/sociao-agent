"""
Scheduler module - APScheduler cron jobs for automated operation.
"""
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from utils.logger import logger
from bot.config import SCRAPE_INTERVAL_HOURS, POST_INTERVAL_MINUTES


# Global scheduler instance
scheduler = AsyncIOScheduler()

# State tracking
_scraper = None
_uploader = None
_notifier = None  # Callback to send Telegram notifications


def set_notifier(callback):
    """Set a callback function to send Telegram notifications."""
    global _notifier
    _notifier = callback


async def _notify(text: str):
    """Send notification via Telegram if notifier is set."""
    if _notifier:
        try:
            await _notifier(text)
        except Exception:
            pass


async def auto_scrape_job():
    """Automated scraping job - runs every SCRAPE_INTERVAL_HOURS."""
    from instagram.scraper import InstagramScraper

    logger.info("⏰ Auto-scrape job triggered")
    try:
        scraper = InstagramScraper()
        added = await scraper.scrape_and_queue(mode="explore", count=20)

        # Also scrape from target accounts
        target_added = await scraper.scrape_and_queue(mode="targets", count=5)
        total = added + target_added

        msg = f"⏰ Auto-Scrape Complete!\n📥 {total} new reels added to queue"
        logger.info(msg)
        await _notify(msg)
    except Exception as e:
        logger.error(f"❌ Auto-scrape failed: {e}")
        await _notify(f"❌ Auto-scrape failed: {e}")


async def auto_post_job():
    """Automated posting job - posts next reel from queue."""
    from instagram.uploader import InstagramUploader
    from database import db

    logger.info("⏰ Auto-post job triggered")
    try:
        # Check daily limit
        today_count = await db.get_today_post_count()
        from bot.config import MAX_POSTS_PER_DAY

        if today_count >= MAX_POSTS_PER_DAY:
            logger.info(f"📊 Daily limit reached ({today_count}/{MAX_POSTS_PER_DAY}), skipping")
            return

        uploader = InstagramUploader()
        result = await uploader.post_next_from_queue()

        if result:
            msg = (
                f"✅ Auto-Post Successful!\n"
                f"📸 Credit: @{result['username']}\n"
                f"📊 Today: {today_count + 1}/{MAX_POSTS_PER_DAY}"
            )
            await _notify(msg)
        else:
            queue_count = await db.get_queue_count()
            if queue_count == 0:
                await _notify("📭 Queue is empty! Use /scrape to find more reels.")
    except Exception as e:
        logger.error(f"❌ Auto-post failed: {e}")
        await _notify(f"❌ Auto-post failed: {e}")


async def cleanup_job():
    """Clean up old downloaded files."""
    from instagram.downloader import InstagramDownloader
    logger.info("🧹 Cleanup job triggered")
    downloader = InstagramDownloader()
    await downloader.cleanup_old_downloads(keep_hours=24)


async def health_check_job():
    """Send a health-check status message every 12 hours."""
    from database import db

    stats = await db.get_stats()
    msg = (
        f"💓 Agent Health Check\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"📊 Today Posts: {stats['today_posts']}/{MAX_POSTS_PER_DAY}\n"
        f"📥 Queue: {stats['queue_size']}\n"
        f"✅ Total Posted: {stats['total_posted']}\n"
        f"❌ Total Failed: {stats['total_failed']}\n"
        f"🔍 Total Scraped: {stats['total_scraped']}\n"
        f"🟢 Scheduler: Running"
    )
    await _notify(msg)


def start_scheduler(
    scrape_interval_hours: int = SCRAPE_INTERVAL_HOURS,
    post_interval_minutes: int = POST_INTERVAL_MINUTES,
):
    """Start all scheduled jobs."""
    if scheduler.running:
        logger.warning("Scheduler already running")
        return

    # Auto-scrape every X hours
    scheduler.add_job(
        auto_scrape_job,
        IntervalTrigger(hours=scrape_interval_hours),
        id="auto_scrape",
        replace_existing=True,
        name="Auto Scrape",
    )

    # Auto-post every X minutes
    scheduler.add_job(
        auto_post_job,
        IntervalTrigger(minutes=post_interval_minutes),
        id="auto_post",
        replace_existing=True,
        name="Auto Post",
    )

    # Cleanup daily at 3 AM
    scheduler.add_job(
        cleanup_job,
        CronTrigger(hour=3, minute=0),
        id="cleanup",
        replace_existing=True,
        name="Daily Cleanup",
    )

    # Health check every 12 hours
    scheduler.add_job(
        health_check_job,
        IntervalTrigger(hours=12),
        id="health_check",
        replace_existing=True,
        name="Health Check",
    )

    scheduler.start()
    logger.info(
        f"⏰ Scheduler started! Scrape every {scrape_interval_hours}h, "
        f"Post every {post_interval_minutes}min"
    )


def stop_scheduler():
    """Stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("⏰ Scheduler stopped")


def is_scheduler_running() -> bool:
    """Check if scheduler is running."""
    return scheduler.running


def update_scrape_interval(hours: int):
    """Update the scrape interval."""
    if scheduler.running:
        scheduler.reschedule_job(
            "auto_scrape",
            trigger=IntervalTrigger(hours=hours),
        )
        logger.info(f"⏰ Scrape interval updated to {hours}h")


def update_post_interval(minutes: int):
    """Update the post interval."""
    if scheduler.running:
        scheduler.reschedule_job(
            "auto_post",
            trigger=IntervalTrigger(minutes=minutes),
        )
        logger.info(f"⏰ Post interval updated to {minutes}min")
