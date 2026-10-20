"""The backtest timeline (Phase 4, Steps 4.1–4.2).

For each trading day T (one ticker per run, EXPERIMENT_PLAN §1), in this exact order:
  1. OPEN  corporate actions from the data: split (split_factor ≠ 1) → dividend (div_cash_usd > 0)
  2. OPEN  orders created at the previous close are filled at T's open_raw (execution.fills)
  3. CLOSE valuation at close_raw → one row of daily equity
  4. CLOSE the strategy sees data up to and including T's close → order intents, queued for T+1
After the last day, orders still queued are EXPIRED (never filled at a made-up price).
No look-ahead: the strategy receives a COPY of the table that physically ends at T, and a
read-only portfolio view. The engine holds no strategy rules and no fee numbers.
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol

import pandas as pd

from quant_research.execution.costs import apply_spread, fee_usd
from quant_research.execution.fills import FillResult, Rejection, fill_order
from quant_research.execution.orders import OrderIntent
from quant_research.portfolio.ledger import Portfolio
from quant_research.portfolio.money import round_receive, to_decimal_price

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ["date", "open_raw", "close_raw", "div_cash_usd", "split_factor"]


@dataclass(frozen=True)
class PortfolioView:
    """Read-only snapshot for strategies — they cannot change the ledger through it."""

    cash_usd: Decimal
    quantity: Decimal
    average_cost_usd: Decimal


class Strategy(Protocol):
    def on_close(
        self, day: date, history: pd.DataFrame, portfolio_view: PortfolioView
    ) -> list[OrderIntent]: ...


@dataclass(frozen=True)
class EngineSettings:
    broker: str
    spread_level: str
    share_mode: str
    min_order_usd: Decimal | None


@dataclass(frozen=True)
class OrderRecord:
    created_day: date  # close at which the strategy asked
    intended_day: date | None  # next open (None if the run ended first)
    intent: OrderIntent
    status: str  # FILLED / REJECTED / EXPIRED
    reason: str | None = None


@dataclass(frozen=True)
class EquityRow:
    day: date
    cash_usd: Decimal
    market_value_usd: Decimal
    total_value_usd: Decimal


@dataclass
class EngineResult:
    ticker: str
    portfolio: Portfolio
    orders: list[OrderRecord] = field(default_factory=list)
    fills: list[FillResult] = field(default_factory=list)
    equity: list[EquityRow] = field(default_factory=list)
    last_close_value_usd: Decimal = Decimal(0)
    liquidation_value_usd: Decimal = Decimal(0)


def _decimal(value: object, what: str, day: date) -> Decimal:
    if hasattr(value, "item"):  # numpy scalar from a pandas row → plain Python number
        value = value.item()
    if value is None or (isinstance(value, float) and math.isnan(value)):
        raise ValueError(f"missing {what} on {day}")
    return to_decimal_price(value)  # the one float → Decimal entry point


def run_engine(
    prices: pd.DataFrame,
    ticker: str,
    strategy: Strategy,
    settings: EngineSettings,
    initial_cash_usd: Decimal,
) -> EngineResult:
    """Run one ticker through the timeline. `prices` = validated loader output (raw columns)."""
    missing = [c for c in REQUIRED_COLUMNS if c not in prices.columns]
    if missing:
        raise ValueError(f"price table is missing columns {missing}")
    if prices.empty:
        raise ValueError("price table is empty")
    table = prices.reset_index(drop=True)
    ticker = ticker.upper()
    ledger = Portfolio(
        initial_cash_usd, share_mode=settings.share_mode, min_order_usd=settings.min_order_usd
    )  # type: ignore[arg-type]
    result = EngineResult(ticker, ledger)
    queued: list[tuple[date, OrderIntent]] = []
    previous_close: Decimal | None = None

    for i in range(len(table)):
        row = table.iloc[i]
        day = row["date"]
        # 1. OPEN — corporate actions: split → dividend
        split = float(row["split_factor"])
        if abs(split - 1.0) > 1e-12:
            ledger.apply_split(day, ticker, to_decimal_price(split))
        dividend = float(row["div_cash_usd"])
        if dividend > 0:
            ledger.apply_dividend(day, ticker, to_decimal_price(dividend))
        # 2. OPEN — fill yesterday's orders at today's open
        if queued:
            open_raw = _decimal(row["open_raw"], f"open price for {ticker}", day)
            for created, intent in queued:
                outcome = fill_order(
                    intent,
                    day,
                    open_raw,
                    ledger,
                    settings.broker,
                    settings.spread_level,
                    settings.share_mode,
                    settings.min_order_usd,
                    previous_close,
                )
                if isinstance(outcome, Rejection):
                    result.orders.append(
                        OrderRecord(created, day, intent, "REJECTED", outcome.reason)
                    )
                    logger.info("order rejected on %s: %s", day, outcome.reason)
                else:
                    result.orders.append(OrderRecord(created, day, intent, "FILLED"))
                    result.fills.append(outcome)
            queued = []
        # 3. CLOSE — valuation
        close = _decimal(row["close_raw"], f"close price for {ticker}", day)
        valuation = ledger.valuation(day, {ticker: close})
        result.equity.append(
            EquityRow(
                day, valuation.cash_usd, valuation.total_market_value_usd, valuation.total_value_usd
            )
        )
        # 4. CLOSE — strategy sees data up to T only (a physical copy ending at T)
        history = table.iloc[: i + 1].copy()
        pos = ledger.position(ticker)
        view = PortfolioView(ledger.cash_usd, pos.quantity, pos.average_cost_usd)
        intents = strategy.on_close(day, history, view)
        for intent in intents or []:
            if not isinstance(intent, OrderIntent):
                raise TypeError(
                    f"strategy must return OrderIntent objects, got {type(intent).__name__}"
                )
            if intent.ticker != ticker:
                raise ValueError(
                    f"order for unknown ticker {intent.ticker!r} (this run trades {ticker})"
                )
            queued.append((day, intent))
        previous_close = close

    # 5. orders left after the last day expire
    for created, intent in queued:
        result.orders.append(
            OrderRecord(created, None, intent, "EXPIRED", "run ended before next open")
        )

    # End: value at last close, and liquidation value (sell at last close after spread + fee)
    last = result.equity[-1]
    result.last_close_value_usd = last.total_value_usd
    qty = ledger.position(ticker).quantity
    liquidation = ledger.cash_usd
    if qty > 0:
        last_close = _decimal(table.iloc[-1]["close_raw"], "last close", last.day)
        sell_fill = apply_spread(last_close, "sell", settings.spread_level, qty).fill_price_usd  # type: ignore[arg-type]
        value = qty * sell_fill
        liquidation += round_receive(value) - fee_usd(settings.broker, value, qty).total_usd
    result.liquidation_value_usd = liquidation
    return result
