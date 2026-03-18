"""
Configuration module - Load env vars and define constants.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Base Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOAD_PATH = Path(os.getenv("DOWNLOAD_PATH", "./downloads"))
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "./data/agent.db"))

# Ensure directories exist
DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMIN_ID = int(os.getenv("TELEGRAM_ADMIN_ID", "0"))

# --- Gemini AI ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# --- Instagram Accounts ---
IG_ACCOUNTS = [
    {
        "username": os.getenv("IG_ACCOUNT_1_USERNAME", ""),
        "password": os.getenv("IG_ACCOUNT_1_PASSWORD", ""),
        "graph_token": os.getenv("IG_ACCOUNT_1_GRAPH_TOKEN", ""),
    },
    {
        "username": os.getenv("IG_ACCOUNT_2_USERNAME", ""),
        "password": os.getenv("IG_ACCOUNT_2_PASSWORD", ""),
        "graph_token": os.getenv("IG_ACCOUNT_2_GRAPH_TOKEN", ""),
    },
]

# Default active account index (0 = first, 1 = second)
DEFAULT_ACTIVE_ACCOUNT = 0

# --- Agent Settings ---
MAX_POSTS_PER_DAY = int(os.getenv("MAX_POSTS_PER_DAY", "10"))
SCRAPE_INTERVAL_HOURS = int(os.getenv("SCRAPE_INTERVAL_HOURS", "4"))
POST_INTERVAL_MINUTES = int(os.getenv("POST_INTERVAL_MINUTES", "30"))
DEFAULT_HASHTAGS = os.getenv("DEFAULT_HASHTAGS", "#repost,#trending,#viral,#explore,#reels").split(",")

# --- Credit Template ---
CREDIT_TEMPLATE = """🎬 Credits: @{original_username}
📌 All rights belong to the original creator @{original_username}
🔄 Reposted with ❤️

{caption_snippet}

{hashtags}"""

# --- Rate Limits ---
MIN_DELAY_BETWEEN_POSTS_SECONDS = 120  # 2 min between posts
MIN_DELAY_BETWEEN_SCRAPES_SECONDS = 60  # 1 min between scrapes
MAX_SCRAPE_RESULTS = 50  # Max reels to scrape per run
