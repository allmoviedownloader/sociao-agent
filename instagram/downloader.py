"""
Instagram Downloader - Download reels to local storage.
"""
import asyncio
import os
from pathlib import Path
from instagrapi import Client
from utils.logger import logger
from utils.helpers import sanitize_filename
from bot.config import DOWNLOAD_PATH, IG_ACCOUNTS, DEFAULT_ACTIVE_ACCOUNT
from database import db


class InstagramDownloader:
    """Download Instagram reels to local storage."""

    def __init__(self, client: Client | None = None, account_index: int = DEFAULT_ACTIVE_ACCOUNT):
        self.cl = client or Client()
        self.account = IG_ACCOUNTS[account_index]
        self.download_dir = DOWNLOAD_PATH
        self.download_dir.mkdir(parents=True, exist_ok=True)

    async def _run_sync(self, func, *args):
        """Run a synchronous function in executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args)

    async def download_reel(self, media_id: str, media_url: str,
                            username: str = "unknown") -> str | None:
        """
        Download a reel by media_id.
        Returns local file path on success, None on failure.
        """
        try:
            filename = sanitize_filename(f"{username}_{media_id}.mp4")
            filepath = self.download_dir / filename

            # If already downloaded, return existing path
            if filepath.exists():
                logger.info(f"📁 Already downloaded: {filename}")
                return str(filepath)

            # Try to download via instagrapi
            try:
                # Use media_pk (numeric ID) to download
                pk = int(media_id)
                path = await self._run_sync(
                    self.cl.clip_download, pk, self.download_dir
                )
                if path and Path(path).exists():
                    # Rename to our naming convention
                    final_path = self.download_dir / filename
                    Path(path).rename(final_path)
                    logger.info(f"⬇️ Downloaded reel: {filename}")

                    # Update queue with local path
                    await db.update_queue_local_path(media_id, str(final_path))
                    return str(final_path)
            except Exception as e:
                logger.warning(f"⚠️ instagrapi download failed, trying direct URL: {e}")

            # Fallback: download directly from URL using requests
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(media_url) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        filepath.write_bytes(content)
                        logger.info(f"⬇️ Downloaded reel via URL: {filename}")
                        await db.update_queue_local_path(media_id, str(filepath))
                        return str(filepath)
                    else:
                        logger.error(f"❌ URL download failed with status {resp.status}")
                        return None

        except Exception as e:
            logger.error(f"❌ Download failed for {media_id}: {e}")
            return None

    async def download_from_queue(self) -> tuple[dict, str] | None:
        """
        Get next item from queue and download it.
        Returns (queue_item, local_path) or None.
        """
        item = await db.get_next_from_queue()
        if not item:
            logger.info("📭 Queue is empty, nothing to download")
            return None

        # If already has local path and file exists, use it
        if item.get("local_path") and Path(item["local_path"]).exists():
            return item, item["local_path"]

        # Download
        local_path = await self.download_reel(
            media_id=item["media_id"],
            media_url=item["media_url"],
            username=item["username"],
        )
        if local_path:
            return item, local_path

        return None

    async def cleanup_old_downloads(self, keep_hours: int = 24):
        """Delete downloaded files older than keep_hours."""
        import time

        now = time.time()
        cutoff = now - (keep_hours * 3600)
        deleted = 0

        for file in self.download_dir.iterdir():
            if file.is_file() and file.stat().st_mtime < cutoff:
                try:
                    file.unlink()
                    deleted += 1
                except Exception:
                    pass

        if deleted:
            logger.info(f"🧹 Cleaned up {deleted} old downloads")
