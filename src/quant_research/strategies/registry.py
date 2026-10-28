"""Strategy names used in config files → strategy objects.

C1 / C2 need SPY prices and E1 needs the company's 8-K events (PREREGISTRATION_V2). Tests pass them in; otherwise
they are loaded from the saved files AFTER the final-test lock check (D8) — never anything dated ≥ 2021.
"""

from collections.abc import Sequence
from datetime import date
from pathlib import Path

import pandas as pd

from quant_research.backtesting.engine import Strategy
from quant_research.backtesting.run import PROJECT_ROOT, RunConfig, check_final_test_lock
from quant_research.news.events import Event
from quant_research.strategies.buy_and_hold import BuyAndHold
from quant_research.strategies.information import (
    EarningsCoolOff,
    MarketGatedPullback,
    MarketTrendGate,
)
from quant_research.strategies.mean_reversion import MeanReversion
from quant_research.strategies.profit_target import (
    FixedProfitTarget,
    PullbackFromPeak,
    TrendFilteredProfitTarget,
    TrendFilteredPullback,
)

STRATEGY_NAMES = (
    "s0_buy_and_hold",
    "s1_profit_target",
    "s2_pullback",
    "s3_mean_reversion",
    "s4_trend_s1",
    "s4_trend_s2",
    "c1_market_gate",
    "c2_market_gated_pullback",
    "e1_earnings_cooloff",
)
MARKET_TICKER = "SPY"
SUBMISSIONS_DIR = PROJECT_ROOT / "data" / "raw" / "sec" / "submissions"


def load_market(config: RunConfig) -> pd.DataFrame:
    """SPY over the run's dates (same warm-up as the stock), after the D8 lock check."""
    from quant_research.data.loader import load_prices, load_prices_with_warmup

    check_final_test_lock(config)
    if config.warmup_start is not None:
        return load_prices_with_warmup(MARKET_TICKER, config.warmup_start, config.start, config.end)
    return load_prices(MARKET_TICKER, config.start, config.end)


EVENT_CUTOFFS = (
    "2020-12-31",
    "2025-12-31",
)  # saved 8-K files: Phase 9 (to 2020) and the final test (to 2025)


def load_company_events(config: RunConfig, sub_dir: Path = SUBMISSIONS_DIR) -> list[Event]:
    """8-K events from the saved files whose cutoff covers the run's end date (the earliest such cutoff).

    Fix (Phase 10): this used to read the 2020 files for every config, so re-running a final-test E1 config from its
    saved settings would silently miss every 2021–2025 earnings event."""
    from quant_research.news.events import load_events

    check_final_test_lock(config)
    covering = [c for c in EVENT_CUTOFFS if date.fromisoformat(c) >= config.end]
    if not covering:
        raise ValueError(f"no saved 8-K files reach {config.end} (cutoffs {EVENT_CUTOFFS})")
    return load_events(config.ticker, sub_dir, covering[0])


def make_strategy(
    config: RunConfig,
    market: pd.DataFrame | None = None,
    events: Sequence[Event] | None = None,
) -> Strategy:
    if config.strategy == "s0_buy_and_hold":
        return BuyAndHold(config.ticker, config.reinvest_min_cash_usd)
    if config.strategy == "s1_profit_target":
        return FixedProfitTarget(
            config.ticker, config.profit_target_x, config.rebuy_dip_y, config.reinvest_min_cash_usd
        )
    if config.strategy == "s2_pullback":
        return PullbackFromPeak(
            config.ticker, config.profit_target_x, config.rebuy_dip_y, config.reinvest_min_cash_usd
        )
    if config.strategy == "s3_mean_reversion":
        return MeanReversion(
            config.ticker, config.mr_k, config.mr_window, config.reinvest_min_cash_usd
        )
    if config.strategy == "s4_trend_s1":
        return TrendFilteredProfitTarget(
            config.ticker, config.profit_target_x, config.rebuy_dip_y, config.reinvest_min_cash_usd
        )
    if config.strategy == "s4_trend_s2":
        return TrendFilteredPullback(
            config.ticker, config.profit_target_x, config.rebuy_dip_y, config.reinvest_min_cash_usd
        )
    if config.strategy == "c1_market_gate":
        return MarketTrendGate(
            config.ticker,
            load_market(config) if market is None else market,
            config.reinvest_min_cash_usd,
        )
    if config.strategy == "c2_market_gated_pullback":
        return MarketGatedPullback(
            config.ticker,
            config.profit_target_x,
            config.rebuy_dip_y,
            config.reinvest_min_cash_usd,
            market=load_market(config) if market is None else market,
        )
    if config.strategy == "e1_earnings_cooloff":
        return EarningsCoolOff(
            config.ticker,
            config.profit_target_x,
            config.rebuy_dip_y,
            config.reinvest_min_cash_usd,
            events=load_company_events(config) if events is None else events,
        )
    raise ValueError(f"unknown strategy {config.strategy!r}")
