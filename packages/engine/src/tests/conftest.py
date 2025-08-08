"""Shared fixtures for all test modules."""

from __future__ import annotations
import os, pytest, httpx
from dotenv import load_dotenv
from .helpers import reset_and_deposit

load_dotenv()  # load .env → os.environ

BASE_URL = os.getenv("API_URL", "http://localhost:8000")
os.environ.setdefault("TEST_ENV", "true")  # disable API-key auth


@pytest.fixture(scope="session")
def client():
    """Session-wide HTTP client that talks to the live API."""
    with httpx.Client(base_url=BASE_URL, timeout=20.0) as c:
        yield c


@pytest.fixture(scope="session")
def funded_client(client, quote: str = "USDT", amount: float = 100_000.0):
    """Session-wide HTTP client that is reset and funded with USDT."""
    # Reset the backend and fund it with USDT
    reset_and_deposit(client, quote, amount)
    return client
