"""Strategy names used in config files → strategy objects."""

from quant_research.backtesting.engine import Strategy
from quant_research.backtesting.run import RunConfig
from quant_research.strategies.buy_and_hold import BuyAndHold
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
)


def make_strategy(config: RunConfig) -> Strategy:
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
    raise ValueError(f"unknown strategy {config.strategy!r}")
