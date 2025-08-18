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
        # UI Configuration
        "APP_TITLE": os.getenv("APP_TITLE", ""),
        "LOGO_FILE": os.getenv("LOGO_FILE", ""),
        "LOCAL_TZ": os.getenv("LOCAL_TZ", "UTC"),
        # UI Settings
        "UI_URL": os.getenv("UI_URL", "http://localhost:8501"),
        "FRESH_WINDOW_S": int(os.getenv("FRESH_WINDOW_S", "300")),
        "N_VISUAL_DEGRADATIONS": int(os.getenv("N_VISUAL_DEGRADATIONS", "12")),
        "SLIDER_MIN": int(os.getenv("SLIDER_MIN", "10")),
        "SLIDER_MAX": int(os.getenv("SLIDER_MAX", "1000")),
        "SLIDER_STEP": int(os.getenv("SLIDER_STEP", "10")),
        "SLIDER_DEFAULT": int(os.getenv("SLIDER_DEFAULT", "100")),
    }
