"""
Instagram Scraper - Discover trending reels using instagrapi.
"""
import asyncio
from instagrapi import Client
from instagrapi.types import Media
from utils.logger import logger
from database import db
from bot.config import IG_ACCOUNTS, DEFAULT_ACTIVE_ACCOUNT, MAX_SCRAPE_RESULTS


class InstagramScraper:
    """Scrape trending reels from Instagram using instagrapi."""

    def __init__(self, account_index: int = DEFAULT_ACTIVE_ACCOUNT):
        self.cl = Client()
        self.account = IG_ACCOUNTS[account_index]
        self.logged_in = False

    async def login(self) -> bool:
        """Login to Instagram (runs in thread to not block async loop)."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.cl.login(
                    self.account["username"],
                    self.account["password"],
                ),
            )
            self.logged_in = True
            logger.info(f"✅ Logged in as @{self.account['username']}")
            return True
        except Exception as e:
            logger.error(f"❌ Login failed for @{self.account['username']}: {e}")
            return False

    async def _run_sync(self, func, *args):
        """Run a synchronous instagrapi function in executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args)

    async def scrape_explore_reels(self, count: int = 20) -> list[dict]:
        """Scrape trending reels from the explore/reels tab."""
        if not self.logged_in:
            if not await self.login():
                return []

        try:
            # Get reels from explore
            medias = await self._run_sync(self.cl.explore_page, count)
            reels = []
            for media in medias:
                if media.media_type == 2 and media.product_type == "clips":
                    reel_data = self._extract_reel_data(media, source="explore")
                    if reel_data:
                        reels.append(reel_data)
            logger.info(f"🔍 Scraped {len(reels)} reels from Explore")
            return reels[:MAX_SCRAPE_RESULTS]
        except Exception as e:
            logger.error(f"❌ Explore scrape error: {e}")
            return []

    async def scrape_hashtag_reels(self, hashtag: str, count: int = 20) -> list[dict]:
        """Scrape reels from a specific hashtag."""
        if not self.logged_in:
            if not await self.login():
                return []

        try:
            tag = hashtag.lstrip("#")
            medias = await self._run_sync(
                self.cl.hashtag_medias_recent, tag, count
            )
            reels = []
            for media in medias:
                if media.media_type == 2 and media.product_type == "clips":
                    reel_data = self._extract_reel_data(media, source=f"#{tag}")
                    if reel_data:
                        reels.append(reel_data)
            logger.info(f"🔍 Scraped {len(reels)} reels from #{tag}")
            return reels[:MAX_SCRAPE_RESULTS]
        except Exception as e:
            logger.error(f"❌ Hashtag scrape error for #{hashtag}: {e}")
            return []

    async def scrape_user_reels(self, username: str, count: int = 10) -> list[dict]:
        """Scrape reels from a specific user/target account."""
        if not self.logged_in:
            if not await self.login():
                return []

        try:
            # Get user ID from username
            user_id = await self._run_sync(self.cl.user_id_from_username, username)
            medias = await self._run_sync(self.cl.user_medias, user_id, count)
            reels = []
            for media in medias:
                if media.media_type == 2 and media.product_type == "clips":
                    reel_data = self._extract_reel_data(media, source=f"@{username}")
                    if reel_data:
                        reels.append(reel_data)
            logger.info(f"🔍 Scraped {len(reels)} reels from @{username}")
            return reels[:MAX_SCRAPE_RESULTS]
        except Exception as e:
            logger.error(f"❌ User scrape error for @{username}: {e}")
            return []

    async def scrape_target_accounts(self, count_per_account: int = 5) -> list[dict]:
        """Scrape reels from all saved target accounts."""
        targets = await db.get_target_accounts()
        all_reels = []
        for username in targets:
            reels = await self.scrape_user_reels(username, count_per_account)
            all_reels.extend(reels)
        logger.info(f"🎯 Scraped {len(all_reels)} reels from {len(targets)} target accounts")
        return all_reels

    def _extract_reel_data(self, media: Media, source: str = "") -> dict | None:
        """Extract useful data from a Media object."""
        try:
            media_id = str(media.pk)
            video_url = str(media.video_url) if media.video_url else None
            if not video_url:
                return None

            return {
                "media_id": media_id,
                "media_url": video_url,
                "username": media.user.username if media.user else "unknown",
                "caption": media.caption_text or "",
                "likes": media.like_count or 0,
                "views": getattr(media, "play_count", 0) or getattr(media, "view_count", 0) or 0,
                "source": source,
            }
        except Exception as e:
            logger.error(f"Error extracting reel data: {e}")
            return None

    async def scrape_and_queue(
        self,
        mode: str = "explore",
        hashtag: str = "",
        username: str = "",
        count: int = 20,
        target_account: str = "",
    ) -> int:
        """
        Scrape reels and add new ones to the queue.
        Returns number of new reels added.
        """
        # Scrape based on mode
        if mode == "explore":
            reels = await self.scrape_explore_reels(count)
        elif mode == "hashtag" and hashtag:
            reels = await self.scrape_hashtag_reels(hashtag, count)
        elif mode == "user" and username:
            reels = await self.scrape_user_reels(username, count)
        elif mode == "targets":
            reels = await self.scrape_target_accounts(count)
        else:
            reels = await self.scrape_explore_reels(count)

        added = 0
        for reel in reels:
            # Skip if already scraped or posted
            if await db.is_already_scraped(reel["media_id"]):
                continue
            if await db.is_already_posted(reel["media_id"]):
                continue

            # Save to scraped + add to queue
            await db.add_scraped_reel(**reel)
            await db.add_to_queue(
                media_id=reel["media_id"],
                media_url=reel["media_url"],
                username=reel["username"],
                caption=reel["caption"],
                target_account=target_account,
            )
            added += 1

        logger.info(f"📥 Added {added} new reels to queue (from {len(reels)} scraped)")
        return added
