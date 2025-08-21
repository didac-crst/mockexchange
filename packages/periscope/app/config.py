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
    # Automatic URL construction from HOST:PORT variables
    engine_host = os.getenv("ENGINE_HOST", "engine")
    engine_port = os.getenv("ENGINE_PORT", "8000")
    periscope_host = os.getenv("PERISCOPE_HOST", "localhost")
    periscope_port = os.getenv("PERISCOPE_PORT", "8501")

    # Allow manual override with API_URL/UI_URL if needed
    # Handle empty strings by treating them as "not set"
    api_url_env = os.getenv("API_URL")
    ui_url_env = os.getenv("UI_URL")

    api_url = (
        api_url_env
        if api_url_env and api_url_env.strip()
        else f"http://{engine_host}:{engine_port}"
    )
    ui_url = (
        ui_url_env
        if ui_url_env and ui_url_env.strip()
        else f"http://{periscope_host}:{periscope_port}"
    )

    return {
        "API_URL": api_url,
        "API_KEY": os.getenv("API_KEY", "dev-key"),
        "REFRESH_SECONDS": int(os.getenv("REFRESH_SECONDS", "60")),
        # 🆕 Which currency to express equity in
        "QUOTE_ASSET": os.getenv("QUOTE_ASSET", "USDT"),
        # UI Configuration
        "APP_TITLE": os.getenv("APP_TITLE", ""),
        "LOGO_FILE": os.getenv("LOGO_FILE", ""),
        "LOCAL_TZ": os.getenv("LOCAL_TZ", "UTC"),
        # UI Settings
        "UI_URL": ui_url,
        "FRESH_WINDOW_S": int(os.getenv("FRESH_WINDOW_S", "60")),
        "N_VISUAL_DEGRADATIONS": int(os.getenv("N_VISUAL_DEGRADATIONS", "60")),
        "SLIDER_MIN": int(os.getenv("SLIDER_MIN", "10")),
        "SLIDER_MAX": int(os.getenv("SLIDER_MAX", "1000")),
        "SLIDER_STEP": int(os.getenv("SLIDER_STEP", "10")),
        "SLIDER_DEFAULT": int(os.getenv("SLIDER_DEFAULT", "100")),
    }
