"""
Instagram Uploader - Post reels with proper credit using instagrapi.
"""
import asyncio
from pathlib import Path
from instagrapi import Client
from utils.logger import logger
from utils.helpers import build_credit_caption
from database import db
from bot.config import IG_ACCOUNTS, DEFAULT_ACTIVE_ACCOUNT, MAX_POSTS_PER_DAY


class InstagramUploader:
    """Upload reels to Instagram with proper credit to original creators."""

    def __init__(self, account_index: int = DEFAULT_ACTIVE_ACCOUNT):
        self.cl = Client()
        self.account_index = account_index
        self.account = IG_ACCOUNTS[account_index]
        self.logged_in = False

    async def _run_sync(self, func, *args, **kwargs):
        """Run a synchronous function in executor."""
        loop = asyncio.get_event_loop()
        if kwargs:
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
        return await loop.run_in_executor(None, func, *args)

    async def login(self) -> bool:
        """Login to Instagram for uploading."""
        try:
            await self._run_sync(
                self.cl.login,
                self.account["username"],
                self.account["password"],
            )
            self.logged_in = True
            logger.info(f"✅ Uploader logged in as @{self.account['username']}")
            return True
        except Exception as e:
            logger.error(f"❌ Uploader login failed: {e}")
            return False

    async def upload_reel(
        self,
        video_path: str,
        original_username: str,
        original_caption: str = "",
        custom_hashtags: list[str] | None = None,
        media_id: str = "",
    ) -> bool:
        """
        Upload a reel to Instagram with credit caption.
        Returns True on success, False on failure.
        """
        if not self.logged_in:
            if not await self.login():
                return False

        # Check daily limit
        today_count = await db.get_today_post_count()
        if today_count >= MAX_POSTS_PER_DAY:
            logger.warning(f"⚠️ Daily limit reached ({today_count}/{MAX_POSTS_PER_DAY})")
            return False

        # Build caption with credit (try AI first, fallback to template)
        try:
            from utils.gemini_ai import generate_caption
            caption = await generate_caption(
                original_username=original_username,
                original_caption=original_caption,
            )
        except Exception:
            caption = build_credit_caption(
                original_username=original_username,
                original_caption=original_caption,
                custom_hashtags=custom_hashtags,
            )

        try:
            video_file = Path(video_path)
            if not video_file.exists():
                logger.error(f"❌ Video file not found: {video_path}")
                return False

            # Upload reel via instagrapi
            result = await self._run_sync(
                self.cl.clip_upload,
                video_file,
                caption,
            )

            if result:
                logger.info(
                    f"✅ Posted reel! Credit: @{original_username} | "
                    f"Account: @{self.account['username']}"
                )

                # Record in database
                await db.mark_as_posted(
                    media_id=media_id,
                    username=original_username,
                    caption_used=caption,
                    posted_by=self.account["username"],
                )

                # Remove from queue
                if media_id:
                    await db.remove_from_queue(media_id)

                # Try to clean up downloaded file
                try:
                    video_file.unlink()
                except Exception:
                    pass

                return True
            else:
                logger.error("❌ Upload returned None/False")
                await db.mark_as_failed(media_id, original_username, "Upload returned empty result")
                return False

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Upload failed: {error_msg}")
            if media_id:
                await db.mark_as_failed(media_id, original_username, error_msg)
            return False

    async def post_next_from_queue(self) -> dict | None:
        """
        Post the next reel from the queue.
        Returns the posted item info or None.
        """
        from instagram.downloader import InstagramDownloader

        # Check daily limit first
        today_count = await db.get_today_post_count()
        if today_count >= MAX_POSTS_PER_DAY:
            logger.warning(f"⚠️ Daily limit reached ({today_count}/{MAX_POSTS_PER_DAY})")
            return None

        # Get next item
        item = await db.get_next_from_queue()
        if not item:
            logger.info("📭 Queue is empty")
            return None

        # Download if needed
        local_path = item.get("local_path")
        if not local_path or not Path(local_path).exists():
            downloader = InstagramDownloader(client=self.cl, account_index=self.account_index)
            result = await downloader.download_reel(
                media_id=item["media_id"],
                media_url=item["media_url"],
                username=item["username"],
            )
            if not result:
                logger.error(f"❌ Could not download reel {item['media_id']}")
                await db.mark_as_failed(item["media_id"], item["username"], "Download failed")
                await db.remove_from_queue(item["media_id"])
                return None
            local_path = result

        # Upload
        success = await self.upload_reel(
            video_path=local_path,
            original_username=item["username"],
            original_caption=item.get("caption", ""),
            media_id=item["media_id"],
        )

        if success:
            return item
        return None
