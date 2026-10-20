"""Order execution at the open (Phase 4, Step 4.3).

`fill_order` turns one OrderIntent into a ledger trade at day T's OPEN (open_raw), after spread
and broker fee from quant_research.execution.costs. Market problems (not enough cash or shares,
below the minimum order, nothing affordable) return a Rejection with a reason — the run continues.
Bugs (bad inputs, missing price, wrong settings) raise errors.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from quant_research.execution.costs import FeeBreakdown, apply_spread, fee_usd
from quant_research.execution.orders import OrderIntent
from quant_research.portfolio.ledger import LedgerEntry, Portfolio
from quant_research.portfolio.money import (
    SHARE_STEP,
    require_decimal,
    round_pay,
    round_receive,
    round_shares_down,
    shares_affordable,
)


@dataclass(frozen=True)
class FillResult:
    day: date
    ticker: str
    side: str
    quantity: Decimal
    reference_price_usd: Decimal  # T's open_raw
    fill_price_usd: Decimal  # after spread + slippage
    spread_cost_usd: Decimal
    fee: FeeBreakdown
    gap_pct: Decimal | None  # open vs previous close (None on the first day)
    entry: LedgerEntry


@dataclass(frozen=True)
class Rejection:
    day: date
    ticker: str
    side: str
    reason: str


def _max_affordable(
    cash: Decimal, fill: Decimal, broker: str, share_mode: str
) -> tuple[Decimal, FeeBreakdown | None]:
    """Most shares with round_pay(qty × fill) + fee(qty) ≤ cash, for fees that grow with size.

    Every broker's fee only grows with value and quantity, so "affordable" is true up to some
    size and false after it. lo = a size that surely fits (priced with the fee for spending ALL
    the cash); hi = a size that surely does not fit beyond (priced with lo's smaller fee).
    A binary search in share steps between them finds the exact maximum.
    """
    if cash <= 0:
        return Decimal(0), None
    step = Decimal(1) if share_mode == "whole" else SHARE_STEP

    def affordable(qty: Decimal) -> bool:
        return round_pay(qty * fill) + fee_usd(broker, qty * fill, qty).total_usd <= cash

    lo = shares_affordable(cash, fill, fee_usd(broker, cash, cash / fill).total_usd, share_mode)
    if lo <= 0:
        return Decimal(0), None
    hi = shares_affordable(cash, fill, fee_usd(broker, lo * fill, lo).total_usd, share_mode)
    lo_steps, hi_steps = int(lo / step), int(hi / step)  # lo is affordable; nothing above hi is
    while lo_steps < hi_steps:
        mid = (lo_steps + hi_steps + 1) // 2
        if affordable(mid * step):
            lo_steps = mid
        else:
            hi_steps = mid - 1
    qty = lo_steps * step
    return qty, fee_usd(broker, qty * fill, qty)


def fill_order(
    intent: OrderIntent,
    day: date,
    open_raw: Decimal,
    ledger: Portfolio,
    broker: str,
    spread_level: str,
    share_mode: str,
    min_order_usd: Decimal | None,
    previous_close_raw: Decimal | None = None,
) -> FillResult | Rejection:
    """Fill `intent` at T's open, or return a Rejection with a reason."""
    if open_raw is None:
        raise ValueError(f"missing open price for {intent.ticker} on {day}")
    reference = require_decimal(open_raw, "open_raw")
    if reference <= 0:
        raise ValueError(f"open price for {intent.ticker} on {day} must be > 0, got {reference}")
    if share_mode != ledger.share_mode:
        raise ValueError(
            f"share_mode {share_mode!r} does not match the ledger's {ledger.share_mode!r}"
        )
    if min_order_usd != ledger.min_order_usd:
        raise ValueError(
            f"min_order_usd {min_order_usd} does not match the ledger's {ledger.min_order_usd}"
        )
    gap = None
    if previous_close_raw is not None:
        prev = require_decimal(previous_close_raw, "previous_close_raw")
        gap = reference / prev - 1

    def reject(reason: str) -> Rejection:
        return Rejection(day, intent.ticker, intent.side, reason)

    fill = apply_spread(reference, intent.side, spread_level, Decimal(1)).fill_price_usd  # type: ignore[arg-type]
    held = ledger.position(intent.ticker).quantity

    if intent.side == "buy":
        if intent.size == "max_affordable":
            qty, fee = _max_affordable(ledger.cash_usd, fill, broker, share_mode)
            if qty <= 0 or fee is None:
                return reject(f"no shares affordable with cash US${ledger.cash_usd}")
        else:
            qty = Decimal(intent.size)  # type: ignore[arg-type]
            if share_mode == "whole" and qty != qty.to_integral_value():
                raise ValueError(f"whole-share mode: buy size must be a whole number, got {qty}")
            qty = round_shares_down(qty, share_mode)
            if qty <= 0:
                raise ValueError(f"buy size rounds down to 0 shares (step {SHARE_STEP})")
            fee = fee_usd(broker, qty * fill, qty)
        value = qty * fill
        if min_order_usd is not None and value < min_order_usd:
            return reject(f"order value US${value} below minimum US${min_order_usd}")
        need = round_pay(value) + fee.total_usd
        if need > ledger.cash_usd:
            return reject(f"needs US${need} but cash is US${ledger.cash_usd}")
        entry = ledger.buy(day, intent.ticker, qty, fill, fee.total_usd)
    else:
        if held == 0:
            return reject(f"no {intent.ticker} shares held")
        qty = held if intent.size == "all" else Decimal(intent.size)  # type: ignore[arg-type]
        if qty > held:
            return reject(f"sell {qty} but only {held} held")
        value = qty * fill
        closing = qty == held
        if min_order_usd is not None and not closing and value < min_order_usd:
            return reject(f"order value US${value} below minimum US${min_order_usd}")
        fee = fee_usd(broker, value, qty)
        if ledger.cash_usd + round_receive(value) - fee.total_usd < 0:
            return reject(f"fee US${fee.total_usd} exceeds proceeds and cash")
        entry = ledger.sell(day, intent.ticker, qty, fill, fee.total_usd)

    spread_cost = abs(fill - reference) * qty
    return FillResult(
        day, intent.ticker, intent.side, qty, reference, fill, spread_cost, fee, gap, entry
    )
