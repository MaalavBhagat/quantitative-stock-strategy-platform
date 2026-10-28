"""Phase 10, Step 10.1 — one end-to-end run on small made-up data (no internet, no files outside tmp_path).

Mocked Tiingo download → save (CSV + .meta.json) → loader (with the 9 validation checks) → run_backtest (engine,
costs, ledger, FX) for S0 and one S4-S2 setting → run record on disk → metrics → Markdown run report → dashboard data
functions. Every expected value below is worked out by hand in the comments.

Made-up prices on 10 real NYSE sessions (4–15 March 2019, no holidays), open = close each day, no dividends/splits.
Costs: Stake US$3 per trade, normal spread 0.05% (buy = open × 1.0005, sell = open × 0.9995), WHOLE shares,
FX fixed at 0.70 USD per AUD with Stake's 0.55% conversion fee in and out.
"""

import json
from datetime import date
from decimal import Decimal
from functools import partial

import httpx
import pytest

from quant_research.backtesting.run import parse_config, run_backtest
from quant_research.dashboard import data as dd
from quant_research.data.loader import load_prices
from quant_research.data.storage import save_raw_prices
from quant_research.data.tiingo import fetch_daily_prices, prices_endpoint
from quant_research.reporting.run_report import build_run_report
from quant_research.strategies.registry import make_strategy

D = Decimal
DAYS = ["2019-03-04", "2019-03-05", "2019-03-06", "2019-03-07", "2019-03-08",
        "2019-03-11", "2019-03-12", "2019-03-13", "2019-03-14", "2019-03-15"]  # fmt: skip
PRICES = [100, 100, 104, 106, 103, 100, 100, 101, 102, 102]
START, END = date(2019, 3, 4), date(2019, 3, 15)


def tiingo_records() -> list[dict]:
    return [
        {"date": f"{d}T00:00:00.000Z", "open": p, "high": p, "low": p, "close": p, "volume": 1_000_000,
         "adjOpen": p, "adjHigh": p, "adjLow": p, "adjClose": p, "adjVolume": 1_000_000,
         "divCash": 0.0, "splitFactor": 1.0}
        for d, p in zip(DAYS, PRICES, strict=True)
    ]  # fmt: skip


def config(strategy: str, **extra) -> dict:
    return {
        "run_name": f"e2e_{strategy}", "strategy": strategy, "ticker": "ZZZ", "start": START, "end": END,
        "broker": "stake", "spread_level": "normal", "share_mode": "whole", "initial_aud": "10000",
        "fx_source": "fixed", "usd_per_aud_start": "0.70", "usd_per_aud_end": "0.70", **extra,
    }  # fmt: skip


@pytest.fixture
def downloaded(tmp_path):
    """The mocked Tiingo download, saved exactly as the real downloader saves it."""
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=tiingo_records())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    df = fetch_daily_prices("ZZZ", START, END, "FAKEKEY", client=client)
    raw = tmp_path / "raw"
    save_raw_prices(
        df, "ZZZ", START, END, prices_endpoint("ZZZ", START, END), raw, repo_dir=tmp_path
    )
    assert len(seen) == 1 and "FAKEKEY" not in str(seen[0].url)  # key only in the header
    assert "FAKEKEY" not in (raw / "ZZZ_2019-03-04_2019-03-15.meta.json").read_text()
    return raw


def test_download_to_dashboard_end_to_end(downloaded, tmp_path):
    loader = partial(load_prices, data_dir=downloaded)
    prices = loader("ZZZ", START, END)  # validation runs inside: an ERROR would raise
    assert prices["close_raw"].tolist() == PRICES

    runs = tmp_path / "runs"
    out = {}
    for name, cfg in (("s0", config("s0_buy_and_hold")),
                      ("s4s2", config("s4_trend_s2", profit_target_x="0.02", rebuy_dip_y="0.02"))):  # fmt: skip
        c = parse_config(cfg)
        out[name] = run_backtest(
            c, make_strategy(c), load_fn=loader, runs_dir=runs, repo_dir=tmp_path
        )

    # FX in: AUD 10,000 × 0.70 = US$7,000.00; fee 0.55% = 38.50 → start cash US$6,961.50
    for o in out.values():
        assert o.summary["start_cash_usd"] == D("6961.50") and o.summary["fx_in_fee_usd"] == D(
            "38.50"
        )

    # S0: day 0 close → buy; day 1 open 100 → 100.05; (6,961.50 − 3) / 100.05 = 69.55 → 69 shares
    #     cost 69 × 100.05 = 6,903.45 + 3 fee → cash 55.05. Never sells.
    #     last close: 69 × 102 + 55.05 = 7,093.05
    #     liquidation: 69 × 101.949 = 7,034.481 → 7,034.48 − 3 + 55.05 = 7,086.53
    #     FX out: fee 7,086.53 × 0.55% = 38.975915 → 38.98 ; (7,086.53 − 38.98) / 0.70 = 10,067.928… → AUD 10,067.92
    s0 = out["s0"].summary
    assert s0["last_close_value_usd"] == D("7093.05")
    assert s0["liquidation_value_usd"] == D("7086.53")
    assert s0["end_aud_after_liquidation"] == D("10067.92")

    # S4-S2 X = Y = 2% (the 200-day trend filter has too little history → never blocks a sell):
    #   day 1 buy 69 @ 100.05 → cash 55.05 ; E = 100.05 → sell level 102.051
    #   day 2 close 104 ≥ 102.051 → sell ; day 3 open 106 → 105.947 ; 69 × 105.947 = 7,310.343 → 7,310.34 − 3
    #     → cash 7,362.39 ; running high P = day 3 close 106 → rebuy level 103.88
    #   day 4 close 103 ≤ 103.88 → buy ; day 5 open 100 → 100.05 ; (7,362.39 − 3) / 100.05 = 73.55 → 73 shares
    #     cost 7,303.65 + 3 → cash 55.74 ; E = 100.05 ; closes 100, 100, 101, 102, 102 never reach 102.051
    #   last close: 73 × 102 + 55.74 = 7,501.74
    #   liquidation: 73 × 101.949 = 7,442.277 → 7,442.27 − 3 + 55.74 = 7,495.01
    #   FX out: fee 7,495.01 × 0.55% = 41.222555 → 41.23 ; (7,495.01 − 41.23) / 0.70 = 10,648.257… → AUD 10,648.25
    s4 = out["s4s2"]
    assert [(f.day.isoformat(), f.side, f.quantity) for f in s4.result.fills] == [
        ("2019-03-05", "buy", D(69)), ("2019-03-07", "sell", D(69)), ("2019-03-11", "buy", D(73)),
    ]  # fmt: skip
    assert s4.summary["last_close_value_usd"] == D("7501.74")
    assert s4.summary["liquidation_value_usd"] == D("7495.01")
    assert s4.summary["end_aud_after_liquidation"] == D("10648.25")
    assert s4.summary["total_fees_usd"] == D("9.00")  # 3 trades × US$3

    # run record on disk (read back through the dashboard layer)
    rec = json.loads((s4.run_dir / "run.json").read_text())
    assert rec["data_provenance"]["file_name"] == "ZZZ_2019-03-04_2019-03-15.csv"
    run, base = (
        dd.load_run(s4.run_dir / "run.json", "validation"),
        dd.load_run(out["s0"].run_dir / "run.json", "validation"),
    )
    eq = dd.equity_table(run)
    # equity at closes: 6,961.50 (day 0, cash) → 6,955.05 (day 1: 69 × 100 + 55.05) is the deepest fall:
    # max drawdown = 6,955.05 / 6,961.50 − 1 = −0.0927%
    assert eq["total_usd"].tolist()[:4] == [6961.50, 6955.05, 7231.05, 7362.39]
    keys = dd.key_results(run, base)
    assert keys["Final value (last close, USD)"] == "US$7,501.74"
    assert keys["Max drawdown"].startswith("-0.09%")
    # total return 7,501.74 / 6,961.50 − 1 = 7.760% ; S0 7,093.05 / 6,961.50 − 1 = 1.890% → excess +5.9 pp
    assert keys["Total return (USD)"] == "7.76%" and keys["Excess vs S0 (pp, USD)"] == "+5.9"
    assert keys["Round trips (sells)"] == "1"

    # Markdown report generated from the record
    report = build_run_report(run, base)
    assert "# Run report — ZZZ · Trend filter + pullback (S4-S2) · X 2% / Y 2%" in report
    assert "| Final value (last close, USD) | US$7,501.74 | US$7,093.05 |" in report
    assert "SIMULATED, HISTORICAL" in report
