"""Strategy names used in config files → strategy objects."""

from quant_research.backtesting.engine import Strategy
from quant_research.backtesting.run import RunConfig
from quant_research.strategies.buy_and_hold import BuyAndHold
from quant_research.strategies.profit_target import FixedProfitTarget, PullbackFromPeak


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
    raise ValueError(f"unknown strategy {config.strategy!r}")
