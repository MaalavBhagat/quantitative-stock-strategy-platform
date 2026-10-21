"""Ambiguous daily bars (Phase 4, Step 4.6; CLAUDE.md "assume the WORSE order").

A daily bar only says open, high, low, close — not whether the high or the low came first.
When a buy level AND a sell level are both inside one bar, we assume the order that is worse for us:
- not holding: assume the HIGH came first (nothing to sell yet), then the low → only the BUY fills;
- holding: assume the LOW came first (we already hold, nothing to rebuy), then the high → only the SELL fills.
So a same-day "buy the dip and sell the rise" profit is never assumed.
Fill prices: a level gapped through at the open fills at the open (buy: open ≤ level; sell: open ≥ level).
NOTE: S0–S4 use the next-open market-order model; this is for later limit-style variants.
"""

from decimal import Decimal

from quant_research.portfolio.money import require_decimal


def resolve_intrabar(
    open_: Decimal,
    high: Decimal,
    low: Decimal,
    close: Decimal,
    buy_level: Decimal | None,
    sell_level: Decimal | None,
    holding: bool,
) -> list[tuple[str, Decimal]]:
    """Events assumed to happen inside the bar, in order: [(side, fill_price), …] (at most one)."""
    o, h, lo, c = (
        require_decimal(x, n)
        for x, n in ((open_, "open"), (high, "high"), (low, "low"), (close, "close"))
    )
    if not (lo <= o <= h and lo <= c <= h):
        raise ValueError(f"inconsistent bar: open {o}, high {h}, low {lo}, close {c}")
    buy = require_decimal(buy_level, "buy_level") if buy_level is not None else None
    sell = require_decimal(sell_level, "sell_level") if sell_level is not None else None
    buy_hit = buy is not None and lo <= buy
    sell_hit = sell is not None and h >= sell
    if holding:
        # worse order: the low (rebuy) is assumed to come first — irrelevant while holding — so only a sell
        return [("sell", max(o, sell))] if sell_hit else []  # type: ignore[type-var]
    return [("buy", min(o, buy))] if buy_hit else []  # type: ignore[type-var]
