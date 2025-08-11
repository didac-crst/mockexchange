# tests/test_cli.py – ensure CLI dispatches to correct HTTP endpoints
from types import SimpleNamespace

import httpx
import pytest


# ---------------------------------------------------------------------------
# Dummy HTTP client – records calls & returns pre-seeded responses
# ---------------------------------------------------------------------------
class DummyClient(SimpleNamespace):
    """Minimal stub mimicking *httpx.Client*.

    *   Keeps a FIFO queue of *httpx.Response* objects to return.
    *   Captures every call (method, path, payload) for later inspection.
    """

    def __init__(self, responses):
        super().__init__(responses=list(responses), calls=[])

    # http verbs ------------------------------------------------------
    def get(self, path, params=None):
        return self._reply("GET", path, params=params)

    def post(self, path, json=None):
        return self._reply("POST", path, json=json)

    def patch(self, path, json=None):
        return self._reply("PATCH", path, json=json)

    def delete(self, path):
        return self._reply("DELETE", path)

    # internal --------------------------------------------------------
    def _reply(self, method, path, **payload):
        self.calls.append((method, path, payload))
        if not self.responses:
            raise RuntimeError("DummyClient: no more stub responses queued")
        return self.responses.pop(0)


# ---------------------------------------------------------------------------
# Helper to execute the CLI with a fake *argv* and fake HTTP client
# ---------------------------------------------------------------------------


def run_cli(monkeypatch, capsys, fake_client, argv):
    """Import the *cli* module fresh, patch the client, run main()."""

    import importlib
    import sys as _sys

    cli = importlib.import_module("mockexchange_api.cli")
    monkeypatch.setattr(cli, "client", fake_client, raising=True)
    monkeypatch.setattr(_sys, "argv", ["mockx", *argv])

    try:
        cli.main()
        code = 0
    except SystemExit as exc:  # *cli* exits with non-zero on HTTP error
        code = exc.code

    stdout = capsys.readouterr().out
    return code, stdout, fake_client.calls


# ---------------------------------------------------------------------------
# Param-driven routing checks
# ---------------------------------------------------------------------------

cases = [
    # cmd-name        argv                                method  path                                   json/params dict
    ("balance", ["balance"], "GET", "/balance", {}),
    ("ticker", ["ticker", "BTC/USDT"], "GET", "/tickers/BTC/USDT", {}),
    (
        "order",
        ["order", "BTC/USDT", "buy", "1"],
        "POST",
        "/orders",
        {
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "market",
            "amount": 1.0,
            "limit_price": None,
        },
    ),
    ("orders", ["orders"], "GET", "/orders", {}),
    # asset deposit helpers -------------------------------------------------
    (
        "deposit",
        ["deposit", "USDT", "100"],
        "POST",
        "/balance/USDT/deposit",
        {"amount": 100.0},
    ),
    # asset withdrawal helpers -------------------------------------------------
    (
        "withdrawal",
        ["withdrawal", "USDT", "100"],
        "POST",
        "/balance/USDT/withdrawal",
        {"amount": 100.0},
    ),
    # single-order fetch -----------------------------------------------------
    ("order-get", ["order-get", "oid123"], "GET", "/orders/oid123", {}),
    # slim list -------------------------------------------------------------
    ("orders-simple", ["orders-simple"], "GET", "/orders/list", {}),
    # dry-run checker -------------------------------------------------------
    (
        "can-exec",
        ["can-exec", "BTC/USDT", "buy", "1"],
        "POST",
        "/orders/can_execute",
        {"symbol": "BTC/USDT", "side": "buy", "amount": 1.0, "price": None},
    ),
    # admin helpers ---------------------------------------------------------
    (
        "set-balance",
        ["set-balance", "DOT", "--free", "10"],
        "PATCH",
        "/admin/balance/DOT",
        {"free": 10.0, "used": 0.0},
    ),
    (
        "set-price",
        ["set-price", "BTC/USDT", "30000"],
        "PATCH",
        "/admin/tickers/BTC/USDT/price",
        {"price": 30000.0, "bid_volume": None, "ask_volume": None},
    ),
    ("reset-data", ["reset-data"], "DELETE", "/admin/data", {}),
    ("health", ["health"], "GET", "/admin/health", {}),
]


@pytest.mark.parametrize("_name, argv, method, path, expected", cases)
def test_cli_routes(_name, argv, method, path, expected, monkeypatch, capsys):
    # every call gets a dummy 200/OK
    fake = DummyClient([httpx.Response(200, json={"ok": True})])
    code, _out, calls = run_cli(monkeypatch, capsys, fake, argv)

    assert code == 0  # CLI should exit cleanly

    # Build the expected payload wrapper the same way cli._get/_post do
    if method in {"POST", "PATCH"}:
        wrapper = {"json": expected}
    elif method == "GET":
        wrapper = {"params": expected}
    else:  # DELETE
        wrapper = {}

    assert calls == [(method, path, wrapper)]
