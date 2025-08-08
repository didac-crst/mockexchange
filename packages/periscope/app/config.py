# config.py
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent.parent.parent / ".env")

@lru_cache
def settings():
    return {
        "API_URL": os.getenv("API_URL", "http://localhost:8000"),
        "API_KEY": os.getenv("API_KEY", "dev-key"),
        "REFRESH_SECONDS": int(os.getenv("REFRESH_SECONDS", "60")),
        # 🆕 Which currency to express equity in
        "QUOTE_ASSET":  os.getenv("QUOTE_ASSET", "USDT"),
    }