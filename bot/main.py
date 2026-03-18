"""
Main Entry Point - Starts the Telegram Bot + Scheduler.
Run: python -m bot.main
"""
import asyncio
import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from bot.config import TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_ID
from bot.commands import router
from database.db import init_db
from utils.logger import logger


async def on_startup(bot: Bot):
    """Run on bot startup."""
    # Initialize database
    await init_db()

    # Send startup notification to admin
    try:
        await bot.send_message(
            TELEGRAM_ADMIN_ID,
            "🟢 *Instagram Repost Agent is ONLINE!*\n\n"
            "Send /start to see all commands.\n"
            "Send /schedule\\_on to start auto mode.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.warning(f"Could not send startup message: {e}")

    logger.info("🟢 Bot is online and ready!")


async def on_shutdown(bot: Bot):
    """Run on bot shutdown."""
    from scheduler.jobs import stop_scheduler

    stop_scheduler()

    try:
        await bot.send_message(
            TELEGRAM_ADMIN_ID,
            "🔴 Agent is shutting down...",
        )
    except Exception:
        pass

    logger.info("🔴 Bot is shutting down")


async def main():
    """Main function - initialize and start the bot."""
    # Validate config
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN not set in .env!")
        sys.exit(1)

    if not TELEGRAM_ADMIN_ID:
        logger.error("❌ TELEGRAM_ADMIN_ID not set in .env!")
        sys.exit(1)

    # Create bot and dispatcher
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()

    # Register router with commands
    dp.include_router(router)

    # Register startup/shutdown hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("🚀 Starting Instagram Repost Agent...")
    logger.info(f"👤 Admin ID: {TELEGRAM_ADMIN_ID}")

    # Start polling
    try:
        await dp.start_polling(bot, allowed_updates=["message"])
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
