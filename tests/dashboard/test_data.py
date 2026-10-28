"""Tests for quant_research.dashboard.data — no Streamlit server needed."""

import json
import re
from datetime import date
from pathlib import Path

import pytest

from quant_research.dashboard import data as dd

EQUITY = "day,cash_usd,market_value_usd,total_value_usd\n"
FILLS = (
    "day,side,quantity,reference_price_usd,fill_price_usd,spread_cost_usd,brokerage_usd,fx_usd,fee_total_usd,"
    "gap_pct,realised_pnl_usd,position_after\n"
)
ORDERS = "created_day,intended_day,side,ticker,size,status,reason\n"


def make_run(tmp_path: Path, name: str = "r1", end: str = "2020-12-31", equity_rows=None, fills_rows=None,
             orders_rows=None) -> Path:  # fmt: skip
    d = tmp_path / name
    d.mkdir()
    record = {
        "run_id": name,
        "config": {
            "strategy": "s1_profit_target", "ticker": "AAA", "end": end, "broker": "stake",
            "spread_level": "normal", "share_mode": "fractional", "fx_source": "rba", "reinvest_min_cash_usd": "100",
            "min_order_usd": "10", "profit_target_x": "0.02", "rebuy_dip_y": "0.04", "mr_k": None,
        },
        "summary": {
            "initial_aud": "10000", "start_cash_usd": "100", "last_close_value_usd": "110",
            "end_aud_after_liquidation": "150", "usd_per_aud_start": "0.7", "usd_per_aud_start_for_day": "2020-01-02",
            "total_fees_usd": "6.00", "dividends_net_usd": "0", "fx_in_fee_usd": "0.55", "fx_out_fee_usd": "0.60",
            "orders": {"FILLED": 2, "REJECTED": 0, "EXPIRED": 1},
        },
        "data_provenance": {"file_name": "AAA.csv", "source": "Tiingo", "downloaded_at_utc": "2026-10-25"},
        "git_commit": "abc", "git_dirty": False, "fx_files": ["x.csv"],
    }  # fmt: skip
    (d / "run.json").write_text(json.dumps(record))
    eq = equity_rows or [
        "2020-01-02,100,0,100",
        "2020-01-03,0,120,120",
        "2020-01-06,0,90,90",
        "2020-01-07,110,0,110",
    ]
    (d / "equity.csv").write_text(EQUITY + "\n".join(eq) + "\n")
    fl = fills_rows or [
        "2020-01-03,buy,1.000000,100,100.05,0.05,3.00,0.00,3.00,0,,1.000000",
        "2020-01-07,sell,1.000000,113,112.94,0.06,3.00,0.00,3.00,0,9.89,0.000000",
    ]
    (d / "fills.csv").write_text(FILLS + "\n".join(fl) + "\n")
    od = orders_rows or [
        "2020-01-02,2020-01-03,buy,AAA,max_affordable,FILLED,",
        "2020-01-06,2020-01-07,sell,AAA,all,FILLED,",
        "2020-01-07,,buy,AAA,max_affordable,EXPIRED,run ended before next open",
    ]
    (d / "orders.csv").write_text(ORDERS + "\n".join(od) + "\n")
    return d / "run.json"


def test_banner_text():
    assert dd.banner("validation") == (
        "SIMULATED, HISTORICAL — not financial advice · Validation period 2017-01-03 → 2020-12-31"
    )
    assert dd.banner("development").startswith(
        "SIMULATED, HISTORICAL — not financial advice · Development"
    )


def test_reading_a_run_record(tmp_path):
    run = dd.load_run(make_run(tmp_path), "validation")
    assert (run.label, run.ticker, run.setting) == ("S1", "AAA", "X 2% / Y 4%")
    assert run.days[0] == date(2020, 1, 2) and run.values == [100.0, 120.0, 90.0, 110.0]
    assert run.total_return == pytest.approx(0.10)
    a = dd.assumptions(run)
    assert a["Broker"] == "stake" and "AAA.csv (Tiingo, downloaded 2026-10-25)" in a["Data files"]
    assert a["Code commit"] == "abc (dirty: False)"


def test_equity_and_drawdown_tables(tmp_path):
    run = dd.load_run(make_run(tmp_path), "validation")
    t = dd.equity_table(run)
    assert list(t["invested_usd"]) == [0, 120, 90, 0]
    # peaks 100, 120, 120, 120 → drawdown 0, 0, −0.25, −0.0833…
    assert list(t["drawdown"]) == pytest.approx([0, 0, -0.25, 110 / 120 - 1])
    k = dd.key_results(run, None)
    assert k["Max drawdown"].startswith("-25.00% (2020-01-03 → 2020-01-06)")
    assert k["Round trips (sells)"] == "1"
    c = dd.costs_table(run)
    assert list(c["cumulative_fees_usd"]) == [3.0, 6.0]
    assert list(c["cumulative_spread_usd"]) == pytest.approx([0.05, 0.11])


def test_not_available_behaviour(tmp_path):
    run = dd.load_run(make_run(tmp_path), "validation")
    assert dd.key_results(run, None)["Excess vs S0 (pp, USD)"] == dd.NOT_AVAILABLE
    assert dd.show(None) == "not available" and dd.show(0.5, "{:.0%}") == "50%"
    effect = dd.trade_effect(
        run, 0
    )  # first fill: no earlier close before 2020-01-02 … there is one (01-02)
    assert effect["Position before → after"] == "0 → 1.000000"
    assert effect["Cash at the previous close (USD)"] == "US$100.00"
    assert effect["Cash at this day's close (USD)"] == "US$0.00"


def test_orders_keep_expired_and_reasons(tmp_path):
    run = dd.load_run(make_run(tmp_path), "validation")
    o = dd.orders_table(run)
    assert list(o["status"]) == ["FILLED", "FILLED", "EXPIRED"]
    assert o["reason"].iloc[2] == "run ended before next open" and o["reason"].iloc[0] == "—"


def test_d8_guard_refuses_2021_dates(tmp_path):
    with pytest.raises(dd.LockedPeriodError, match="D8"):
        dd.load_run(make_run(tmp_path, "late_end", end="2021-03-31"), "validation")
    with pytest.raises(dd.LockedPeriodError, match="equity"):
        dd.load_run(make_run(tmp_path, "late_eq", equity_rows=["2020-12-31,100,0,100", "2021-01-04,100,0,100"]),
                    "validation")  # fmt: skip
    with pytest.raises(dd.LockedPeriodError):
        dd.check_dates([date(2021, 1, 1)], "x")
    dd.check_dates([date(2020, 12, 31)], "x")  # the last allowed day passes


def test_run_index_rejects_unknown_period(tmp_path):
    with pytest.raises(ValueError):
        dd.run_index("nonsense", tmp_path)


# ---------- consistency with the saved validation report (real local records; skipped without them) ----------
REAL = dd.RUNS_DIR / "validation" / "main"
REPORT = dd.REPORTS_DIR / "experiments" / "validation_2017-2020.md"


@pytest.mark.skipif(not REAL.exists(), reason="local run records (data/, git-ignored) not present")
def test_consistency_s4s2_aapl_with_appendix_b():
    idx = dd.run_index("validation")
    run = dd.load_run(idx[("S4-S2", "AAPL", "X 2% / Y 4%")], "validation")
    text = REPORT.read_text(encoding="utf-8")
    appendix = text[text.index("## Appendix B") : text.index("## Appendix C")]
    report_fills = re.findall(r"^\| \d+ \| \d{4}-\d{2}-\d{2} \|", appendix, flags=re.MULTILINE)
    final = re.search(r"final value at last close US\$([\d,]+\.\d\d)", appendix).group(1)
    k = dd.key_results(run, None)
    assert final == "22,849.41"
    assert k["Final value (last close, USD)"] == f"US${final}"
    assert len(run.fills) == len(report_fills) == 23
    # this run's max drawdown is not in the report → checked against an independent peak/trough loop here
    peak, worst = run.values[0], 0.0
    for v in run.values:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    assert k["Max drawdown"].startswith(f"{worst:.2%}")
    # S0 AAPL max drawdown IS in the report (§2: "max DD -38.46%")
    s0 = dd.load_run(idx[("S0", "AAPL", "—")], "validation")
    assert dd.key_results(s0, None)["Max drawdown"].startswith("-38.46%")
    assert "max DD -38.46%" in text


@pytest.mark.skipif(not REPORT.exists(), reason="validation report missing")
def test_verdict_table_is_copied_from_the_report():
    t = dd.verdict_table()
    assert not t.startswith("## ") and t.count("**REJECTED**") == 5
    assert t in REPORT.read_text(encoding="utf-8")


@pytest.mark.skipif(not dd.PHASE9_REPORT.exists(), reason="Phase 9 report missing")
def test_phase9_verdicts_are_found_by_strategy_id():
    for sid in ("C1", "C2", "E1"):
        rows = [ln for ln in dd.verdict_for(sid).splitlines()[2:]]
        assert len(rows) == 1 and f"({sid}) (vs " in rows[0]
    assert "PREREGISTRATION_V2" in dd.verdict_source("E1")
    assert "validation_2017-2020" in dd.verdict_source("S4-S2")
    assert dd.verdict_for("S4-S2").splitlines()[2].split("|")[1].strip() == "S4-S2"


def test_final_period_shows_2021_2025_but_nothing_later(tmp_path):
    ok = make_run(tmp_path, "final_ok", end="2025-12-31",
                  equity_rows=["2025-12-30,100,0,100", "2025-12-31,100,0,100"],
                  fills_rows=["2025-12-30,buy,1.000000,100,100.05,0.05,3.00,0.00,3.00,0,,1.000000"],
                  orders_rows=["2025-12-29,2025-12-30,buy,AAA,max_affordable,FILLED,"])  # fmt: skip
    assert dd.load_run(ok, "final").days[-1] == date(2025, 12, 31)
    with pytest.raises(dd.LockedPeriodError):  # the same record is refused on any other page
        dd.load_run(ok, "validation")
    late = make_run(tmp_path, "final_late", end="2026-01-02")
    with pytest.raises(dd.LockedPeriodError, match="2026-01-01"):
        dd.load_run(late, "final")


@pytest.mark.skipif(not dd.FINAL_REPORT.exists(), reason="final test report missing")
def test_final_verdicts_are_found_by_strategy_id():
    for sid in ("S1", "S2", "S3", "S4-S1", "S4-S2", "C1", "C2", "E1"):
        rows = dd.verdict_for(sid, "final").splitlines()[2:]
        assert len(rows) == 1 and f"({sid}) (vs " in rows[0]
    assert "FINAL_TEST_PREREG" in dd.verdict_source("S1", "final")
    assert dd.verdict_for("S0", "final") is None


def test_display_formatting_cents_shares_and_dash(tmp_path):
    rows = [
        "2020-01-03,buy,1.2345678,100,100.05,0.005,3.00,0.00,3.00,0,,1.234567",
        "2020-01-07,sell,1.234567,113,112.94,0.015,3.00,0.00,3.00,0,9.885,0.000000",
    ]
    t = dd.fills_table(dd.load_run(make_run(tmp_path, fills_rows=rows), "validation"))
    # ROUND_HALF_EVEN to cents: 0.005 → 0.00, 0.015 → 0.02, 9.885 → 9.88
    assert list(t["spread cost (USD)"]) == ["0.00", "0.02"]
    assert t["realised P&L (USD)"].iloc[1] == "9.88"
    assert t["realised P&L (USD)"].iloc[0] == "—"  # a buy: not applicable (not "not available")
    assert t["shares"].iloc[0] == "1.234568" and t["position after"].iloc[1] == "0.000000"
    assert t["fill (USD)"].iloc[0] == "100.05"  # prices exactly as stored
    assert list(t["fee (USD)"]) == ["3.00", "3.00"]
