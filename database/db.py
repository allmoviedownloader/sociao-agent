"""
Database module - SQLite async database for tracking reels.
"""
import aiosqlite
from pathlib import Path
from bot.config import DATABASE_PATH
from utils.logger import logger


async def init_db():
    """Initialize database tables."""
    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS scraped_reels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_id TEXT UNIQUE NOT NULL,
                media_url TEXT,
                username TEXT NOT NULL,
                caption TEXT DEFAULT '',
                likes INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'explore'
            );

            CREATE TABLE IF NOT EXISTS post_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_id TEXT UNIQUE NOT NULL,
                media_url TEXT,
                username TEXT NOT NULL,
                caption TEXT DEFAULT '',
                local_path TEXT,
                target_account TEXT DEFAULT '',
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                priority INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS posted_reels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_id TEXT NOT NULL,
                username TEXT NOT NULL,
                caption_used TEXT DEFAULT '',
                posted_by TEXT NOT NULL,
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS failed_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_id TEXT NOT NULL,
                username TEXT NOT NULL,
                error TEXT DEFAULT '',
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS target_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                posts_count INTEGER DEFAULT 0,
                scrapes_count INTEGER DEFAULT 0,
                failures_count INTEGER DEFAULT 0
            );
        """)
        await db.commit()
    logger.info("✅ Database initialized successfully")


async def is_already_scraped(media_id: str) -> bool:
    """Check if a reel has already been scraped."""
    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        cursor = await db.execute(
            "SELECT 1 FROM scraped_reels WHERE media_id = ?", (media_id,)
        )
        return await cursor.fetchone() is not None


async def is_already_posted(media_id: str) -> bool:
    """Check if a reel has already been posted."""
    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        cursor = await db.execute(
            "SELECT 1 FROM posted_reels WHERE media_id = ?", (media_id,)
        )
        return await cursor.fetchone() is not None


async def add_scraped_reel(media_id: str, media_url: str, username: str,
                           caption: str = "", likes: int = 0, views: int = 0,
                           source: str = "explore"):
    """Add a scraped reel to the database."""
    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        try:
            await db.execute(
                """INSERT OR IGNORE INTO scraped_reels
                   (media_id, media_url, username, caption, likes, views, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (media_id, media_url, username, caption, likes, views, source),
            )
            await db.commit()
        except Exception as e:
            logger.error(f"DB error adding scraped reel: {e}")


async def add_to_queue(media_id: str, media_url: str, username: str,
                       caption: str = "", target_account: str = "",
                       priority: int = 0):
    """Add a reel to the post queue."""
    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        try:
            await db.execute(
                """INSERT OR IGNORE INTO post_queue
                   (media_id, media_url, username, caption, target_account, priority)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (media_id, media_url, username, caption, target_account, priority),
            )
            await db.commit()
        except Exception as e:
            logger.error(f"DB error adding to queue: {e}")


async def get_next_from_queue(target_account: str = "") -> dict | None:
    """Get the next reel from the queue."""
    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        db.row_factory = aiosqlite.Row
        if target_account:
            cursor = await db.execute(
                """SELECT * FROM post_queue
                   WHERE target_account = ? OR target_account = ''
                   ORDER BY priority DESC, added_at ASC LIMIT 1""",
                (target_account,),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM post_queue ORDER BY priority DESC, added_at ASC LIMIT 1"
            )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def remove_from_queue(media_id: str):
    """Remove a reel from the queue."""
    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        await db.execute("DELETE FROM post_queue WHERE media_id = ?", (media_id,))
        await db.commit()


async def update_queue_local_path(media_id: str, local_path: str):
    """Update the local file path of a queued reel."""
    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        await db.execute(
            "UPDATE post_queue SET local_path = ? WHERE media_id = ?",
            (local_path, media_id),
        )
        await db.commit()


async def mark_as_posted(media_id: str, username: str, caption_used: str,
                         posted_by: str):
    """Record a successful post."""
    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        await db.execute(
            """INSERT INTO posted_reels (media_id, username, caption_used, posted_by)
               VALUES (?, ?, ?, ?)""",
            (media_id, username, caption_used, posted_by),
        )
        # Update daily stats
        await db.execute(
            """INSERT INTO daily_stats (date, posts_count)
               VALUES (date('now'), 1)
               ON CONFLICT(date) DO UPDATE SET posts_count = posts_count + 1""",
        )
        await db.commit()


async def mark_as_failed(media_id: str, username: str, error: str):
    """Record a failed post attempt."""
    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        await db.execute(
            """INSERT INTO failed_posts (media_id, username, error)
               VALUES (?, ?, ?)""",
            (media_id, username, error),
        )
        await db.execute(
            """INSERT INTO daily_stats (date, failures_count)
               VALUES (date('now'), 1)
               ON CONFLICT(date) DO UPDATE SET failures_count = failures_count + 1""",
        )
        await db.commit()


async def get_queue_count() -> int:
    """Get number of reels in queue."""
    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM post_queue")
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_queue_list(limit: int = 10) -> list[dict]:
    """Get list of queued reels."""
    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM post_queue ORDER BY priority DESC, added_at ASC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_today_post_count() -> int:
    """Get number of posts made today."""
    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        cursor = await db.execute(
            "SELECT posts_count FROM daily_stats WHERE date = date('now')"
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_stats() -> dict:
    """Get overall stats."""
    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        total_scraped = (await (await db.execute("SELECT COUNT(*) FROM scraped_reels")).fetchone())[0]
        total_posted = (await (await db.execute("SELECT COUNT(*) FROM posted_reels")).fetchone())[0]
        total_failed = (await (await db.execute("SELECT COUNT(*) FROM failed_posts")).fetchone())[0]
        queue_size = (await (await db.execute("SELECT COUNT(*) FROM post_queue")).fetchone())[0]
        today_posts = await get_today_post_count()

        return {
            "total_scraped": total_scraped,
            "total_posted": total_posted,
            "total_failed": total_failed,
            "queue_size": queue_size,
            "today_posts": today_posts,
        }


# --- Target Accounts ---
async def add_target_account(username: str):
    """Add a target account to scrape from."""
    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        await db.execute(
            "INSERT OR IGNORE INTO target_accounts (username) VALUES (?)",
            (username,),
        )
        await db.commit()


async def remove_target_account(username: str):
    """Remove a target account."""
    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        await db.execute(
            "DELETE FROM target_accounts WHERE username = ?", (username,)
        )
        await db.commit()


async def get_target_accounts() -> list[str]:
    """Get all active target accounts."""
    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        cursor = await db.execute(
            "SELECT username FROM target_accounts WHERE active = 1"
        )
        rows = await cursor.fetchall()
        return [r[0] for r in rows]
