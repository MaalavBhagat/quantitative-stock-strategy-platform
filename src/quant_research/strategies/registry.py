"""Strategy names used in config files → strategy objects."""

from quant_research.backtesting.engine import Strategy
from quant_research.backtesting.run import RunConfig
from quant_research.strategies.buy_and_hold import BuyAndHold


def make_strategy(config: RunConfig) -> Strategy:
    if config.strategy == "s0_buy_and_hold":
        return BuyAndHold(config.ticker, config.reinvest_min_cash_usd)
    raise ValueError(f"unknown strategy {config.strategy!r}")
