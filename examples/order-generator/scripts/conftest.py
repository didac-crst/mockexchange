"""Shared fixtures for all test modules."""

from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv

load_dotenv()  # load .env → os.environ

BASE_URL = os.getenv("API_URL", "http://localhost:8000")
os.environ.setdefault("TEST_ENV", "true")  # disable API-key auth


def client():
    """Session-wide HTTP client that talks to the live API."""
    with httpx.Client(base_url=BASE_URL, timeout=20.0) as c:
        yield c
