"""RunConfig, final-test lock (D8) and run record — synthetic data, temporary folders."""

import csv
import json
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from quant_research.backtesting.run import (
    FinalTestLockedError,
    check_final_test_lock,
    load_config,
    parse_config,
    run_backtest,
)
from quant_research.backtesting.synthetic import make_prices
from quant_research.data.loader import Provenance
from quant_research.execution.orders import OrderIntent

D = Decimal
EXAMPLE = Path(__file__).resolve().parents[2] / "config" / "s0_buy_and_hold_aapl_dev.yaml"


def base_config(**changes):
    # tests never use real RBA data: fixed made-up rates unless a test passes its own FxSeries
    defaults = {"fx_source": "fixed", "usd_per_aud_start": D("0.69"), "usd_per_aud_end": D("0.69")}
    return replace(
        load_config(EXAMPLE), ticker="TEST", share_mode="whole", **{**defaults, **changes}
    )


class BuyTenOnFirstClose:
    def __init__(self):
        self.done = False

    def on_close(self, day, history, view):
        if self.done:
            return []
        self.done = True
        return [OrderIntent("buy", "TEST", D(10))]


def fake_loader(calls: list):
    def load(ticker, start, end):
        calls.append((ticker, start, end))
        prices = make_prices(opens=[100, 100, 110], closes=[100, 100, 110], start=start)
        prices.attrs["provenance"] = Provenance(
            "TEST_fake.csv", "synthetic", "2026-10-20T00:00:00+00:00", "abc", 3
        )
        return prices

    return load


def test_example_config_loads():
    c = load_config(EXAMPLE)
    assert (c.ticker, c.start, c.end, c.broker, c.final_test_unlocked) == (
        "AAPL",
        date(2010, 1, 4),
        date(2016, 12, 30),
        "stake",
        False,
    )
    assert c.initial_aud == D(10000)
    assert (c.fx_source, c.usd_per_aud_start, c.reinvest_min_cash_usd) == ("rba", None, D(100))


def test_config_rejects_floats_unknown_keys_and_bad_dates():
    raw = {
        "run_name": "x",
        "strategy": "s",
        "ticker": "T",
        "start": date(2010, 1, 4),
        "end": date(2010, 2, 1),
        "broker": "stake",
        "spread_level": "normal",
        "share_mode": "whole",
        "initial_aud": "10000",
        "fx_source": "fixed",
        "usd_per_aud_start": "0.69",
        "usd_per_aud_end": "0.69",
    }
    assert parse_config(raw).end == date(2010, 2, 1)
    with pytest.raises(TypeError, match="quotes"):
        parse_config({**raw, "usd_per_aud_start": 0.69})
    with pytest.raises(ValueError, match="unknown config keys"):
        parse_config({**raw, "colour": "blue"})
    with pytest.raises(TypeError, match="date"):
        parse_config({**raw, "start": "2010-01-04x"})
    with pytest.raises(ValueError, match="before start"):
        parse_config({**raw, "end": date(2009, 1, 1)})
    with pytest.raises(TypeError, match="true or false"):
        parse_config({**raw, "final_test_unlocked": "yes"})
    with pytest.raises(ValueError, match="needs usd_per_aud_start"):
        parse_config({**raw, "usd_per_aud_end": None})
    with pytest.raises(ValueError, match="fx_source"):
        parse_config({**raw, "fx_source": "yahoo"})


def test_final_test_lock_refuses_before_loading_anything(tmp_path):
    calls: list = []
    for cfg in (
        base_config(end=date(2021, 6, 30)),
        base_config(start=date(2021, 1, 4), end=date(2021, 3, 1)),
        base_config(end=date(2021, 1, 1)),  # first locked day itself
    ):
        with pytest.raises(FinalTestLockedError, match="locked"):
            run_backtest(cfg, BuyTenOnFirstClose(), load_fn=fake_loader(calls), runs_dir=tmp_path)
    assert calls == []  # the loader was never called
    assert list(tmp_path.iterdir()) == []  # no run folder created


def test_final_test_lock_open_only_when_unlocked():
    check_final_test_lock(base_config(end=date(2020, 12, 31)))  # last dev/validation day is fine
    check_final_test_lock(base_config(end=date(2021, 6, 30), final_test_unlocked=True))


def test_run_record_contents(tmp_path):
    calls: list = []
    cfg = base_config(start=date(2014, 6, 2), end=date(2014, 6, 4), usd_per_aud_end=D("0.75"))
    out = run_backtest(cfg, BuyTenOnFirstClose(), load_fn=fake_loader(calls), runs_dir=tmp_path)
    assert calls == [("TEST", date(2014, 6, 2), date(2014, 6, 4))]
    files = sorted(p.name for p in out.run_dir.iterdir())
    assert files == ["config.yaml", "equity.csv", "fills.csv", "orders.csv", "run.json"]
    record = json.loads((out.run_dir / "run.json").read_text())
    assert record["run_id"] == out.run_id and out.run_id.endswith(cfg.run_name)
    assert record["data_provenance"]["file_name"] == "TEST_fake.csv"
    assert {"git_commit", "git_dirty", "started_utc", "finished_utc", "config", "summary"} <= set(
        record
    )
    assert record["config"]["final_test_unlocked"] is False
    # hand calculation of the summary:
    # AUD 10,000 × 0.69 = 6,900.00 − FX 37.95 = 6,862.05 start cash
    # buy 10 at day-2 open 100 × 1.0005 = 100.05 → 1,000.50 + fee 3.00 → cash 5,858.55
    # liquidation at last close 110: 10 × 109.945 = 1,099.45 − 3.00 = 1,096.45 → 6,955.00
    # USD→AUD at 0.75: fee 0.55% × 6,955.00 = 38.2525 → 38.26 ; (6,955.00 − 38.26) / 0.75 = 9,222.32
    s = record["summary"]
    assert (s["start_cash_usd"], s["liquidation_value_usd"], s["end_aud_after_liquidation"]) == (
        "6862.05",
        "6955.00",
        "9222.32",
    )
    assert s["orders"] == {"FILLED": 1, "REJECTED": 0, "EXPIRED": 0}
    with (out.run_dir / "equity.csv").open() as f:
        equity = list(csv.DictReader(f))
    assert len(equity) == 3 and equity[-1]["total_value_usd"] == "6958.55"  # 5,858.55 + 1,100.00
    with (out.run_dir / "fills.csv").open() as f:
        (fill,) = list(csv.DictReader(f))
    # compare as exact numbers (the text form of 100 may be "100.0" — same value)
    assert (
        D(fill["reference_price_usd"]),
        D(fill["fill_price_usd"]),
        D(fill["fee_total_usd"]),
    ) == (D(100), D("100.05"), D("3.00"))


def test_rba_fx_uses_first_trade_day_and_last_day_rates(tmp_path):
    from quant_research.data.fx import build_series

    # made-up series: 2 June 0.60, 3 June 0.69 (first trade day = day 2), 4 June 0.75 (last day)
    fx = build_series(
        [
            (date(2014, 6, 2), D("0.60")),
            (date(2014, 6, 3), D("0.69")),
            (date(2014, 6, 4), D("0.75")),
        ]
    )
    cfg = base_config(
        fx_source="rba",
        usd_per_aud_start=None,
        usd_per_aud_end=None,
        start=date(2014, 6, 2),
        end=date(2014, 6, 4),
    )
    out = run_backtest(
        cfg, BuyTenOnFirstClose(), load_fn=fake_loader([]), runs_dir=tmp_path, fx_series=fx
    )
    # same numbers as test_run_record_contents (0.69 in, 0.75 out) → 6,862.05 start, AUD 9,222.32 end
    s = out.summary
    assert (s["usd_per_aud_start"], s["usd_per_aud_start_for_day"]) == (D("0.69"), date(2014, 6, 3))
    assert (s["usd_per_aud_end"], s["usd_per_aud_end_for_day"]) == (D("0.75"), date(2014, 6, 4))
    assert (s["start_cash_usd"], s["end_aud_after_liquidation"]) == (D("6862.05"), D("9222.32"))


def test_xy_config_must_be_on_the_grid():
    base = {
        "run_name": "s1",
        "strategy": "s1_profit_target",
        "ticker": "T",
        "start": date(2010, 1, 4),
        "end": date(2010, 2, 1),
        "broker": "stake",
        "spread_level": "normal",
        "share_mode": "fractional",
        "initial_aud": "10000",
        "fx_source": "fixed",
        "usd_per_aud_start": "0.69",
        "usd_per_aud_end": "0.69",
        "profit_target_x": "0.03",
        "rebuy_dip_y": "0.05",
    }
    c = parse_config(base)
    assert (c.profit_target_x, c.rebuy_dip_y, c.grid_override) == (D("0.03"), D("0.05"), False)
    with pytest.raises(ValueError, match="outside the grid"):
        parse_config({**base, "profit_target_x": "0.0317"})
    with pytest.raises(ValueError, match="needs rebuy_dip_y"):
        parse_config({k: v for k, v in base.items() if k != "rebuy_dip_y"})
    with pytest.raises(TypeError, match="quotes"):
        parse_config({**base, "rebuy_dip_y": 0.05})
    with pytest.raises(ValueError, match="between 0 and 1"):
        parse_config({**base, "profit_target_x": "3", "grid_override": True})
    # grid_override allows an exploratory value (logged as a warning)
    assert parse_config(
        {**base, "profit_target_x": "0.0317", "grid_override": True}
    ).profit_target_x == D("0.0317")
    # X/Y on a strategy that doesn't use them is an error
    with pytest.raises(ValueError, match="only for"):
        parse_config({**base, "strategy": "s0_buy_and_hold"})


def test_s3_config_grid_and_warmup_checks():
    base = {
        "run_name": "s3",
        "strategy": "s3_mean_reversion",
        "ticker": "T",
        "start": date(2010, 1, 4),
        "end": date(2010, 2, 1),
        "warmup_start": date(2008, 1, 1),
        "broker": "stake",
        "spread_level": "normal",
        "share_mode": "fractional",
        "initial_aud": "10000",
        "fx_source": "fixed",
        "usd_per_aud_start": "0.69",
        "usd_per_aud_end": "0.69",
        "mr_k": "2.0",
        "mr_window": 20,
    }
    c = parse_config(base)
    assert (c.mr_k, c.mr_window, c.warmup_start) == (D("2.0"), 20, date(2008, 1, 1))
    with pytest.raises(ValueError, match="outside the grid"):
        parse_config({**base, "mr_window": 30})
    with pytest.raises(ValueError, match="outside the grid"):
        parse_config({**base, "mr_k": "1.0"})
    with pytest.raises(ValueError, match="needs mr_k"):
        parse_config({k: v for k, v in base.items() if k != "mr_k"})
    with pytest.raises(ValueError, match="before start"):
        parse_config({**base, "warmup_start": date(2010, 1, 4)})
    with pytest.raises(ValueError, match="only for s3"):
        parse_config({**base, "strategy": "s0_buy_and_hold"})
    s4 = {
        **{k: v for k, v in base.items() if k not in ("mr_k", "mr_window")},
        "strategy": "s4_trend_s1",
    }
    with pytest.raises(ValueError, match="needs profit_target_x"):
        parse_config(s4)
    assert (
        parse_config({**s4, "profit_target_x": "0.05", "rebuy_dip_y": "0.05"}).strategy
        == "s4_trend_s1"
    )


def test_saved_config_yaml_reads_back_unchanged(tmp_path):
    import yaml

    from quant_research.backtesting.run import config_to_yaml

    cfg = base_config(start=date(2014, 6, 2), end=date(2014, 6, 4), usd_per_aud_end=D("0.75"))
    assert parse_config(yaml.safe_load(config_to_yaml(cfg))) == cfg
    out = run_backtest(cfg, BuyTenOnFirstClose(), load_fn=fake_loader([]), runs_dir=tmp_path)
    assert parse_config(yaml.safe_load((out.run_dir / "config.yaml").read_text())) == cfg
