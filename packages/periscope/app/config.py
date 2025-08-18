# config.py
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Try to load .env from multiple possible locations
env_paths = [
    Path(__file__).parent.parent.parent / ".env",  # From periscope package
    Path("/opt/app/.env"),  # From container root
    Path("/.env"),  # From container root (alternative)
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break


@lru_cache
def settings():
    return {
        "API_URL": os.getenv("API_URL", "http://engine:8000"),
        "API_KEY": os.getenv("API_KEY", "dev-key"),
        "REFRESH_SECONDS": int(os.getenv("REFRESH_SECONDS", "60")),
        # 🆕 Which currency to express equity in
        "QUOTE_ASSET": os.getenv("QUOTE_ASSET", "USDT"),
    }
