"""Exact money and share numbers for the ledger (D1, D2, D3 in PROJECT_GUIDE §4).

All ledger amounts are Decimal. A float never enters the ledger directly: prices from the
data (floats) are converted at one place, `to_decimal_price`.
"""

import math
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, InvalidOperation

CENT = Decimal("0.01")
SHARE_DECIMALS = 6  # D3 [ASSUMPTION — Stake's real precision not stated, BROKER_FEES §4]
SHARE_STEP = Decimal(1).scaleb(-SHARE_DECIMALS)  # 0.000001


def to_decimal_price(x: float) -> Decimal:
    """Convert a float price from the data into a Decimal — the ONE float→Decimal entry point.

    Uses the float's shortest text form (so 0.1 becomes exactly 0.1, not 0.1000000000000000055…).
    Rejects NaN, infinity and booleans.
    """
    if isinstance(x, bool) or not isinstance(x, (float, int)):
        raise TypeError(f"to_decimal_price expects a float or int, got {type(x).__name__}")
    if isinstance(x, float) and not math.isfinite(x):
        raise ValueError(f"price is not a finite number: {x}")
    return Decimal(repr(x)) if isinstance(x, float) else Decimal(x)


def require_decimal(value: object, name: str) -> Decimal:
    """Accept Decimal, int or a numeric string; reject floats (and anything else) loudly."""
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a Decimal, int or string — got a bool")
    if isinstance(value, float):
        raise TypeError(
            f"{name} is a float ({value!r}) — floats are not allowed in the ledger; "
            "convert prices with to_decimal_price() or pass a Decimal / string"
        )
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, (int, str)):
        try:
            result = Decimal(value)
        except InvalidOperation:
            raise ValueError(f"{name} is not a number: {value!r}") from None
    else:
        raise TypeError(f"{name} must be a Decimal, int or string — got {type(value).__name__}")
    if not result.is_finite():
        raise ValueError(f"{name} is not a finite number: {value!r}")
    return result


def round_pay(amount_usd: Decimal) -> Decimal:
    """Money we PAY: round UP to the cent (D2, against us)."""
    return amount_usd.quantize(CENT, rounding=ROUND_CEILING)


def round_receive(amount_usd: Decimal) -> Decimal:
    """Money we RECEIVE: round DOWN to the cent (D2, against us)."""
    return amount_usd.quantize(CENT, rounding=ROUND_FLOOR)


def round_shares_down(quantity: Decimal, share_mode: str) -> Decimal:
    """Shares we BUY: whole mode → whole number; fractional → 6 dp; always rounded DOWN (D3)."""
    if share_mode == "whole":
        return quantity.quantize(Decimal(1), rounding=ROUND_FLOOR)
    if share_mode == "fractional":
        return quantity.quantize(SHARE_STEP, rounding=ROUND_FLOOR)
    raise ValueError(f"share_mode must be 'whole' or 'fractional', got {share_mode!r}")


def shares_affordable(
    cash_usd: Decimal, price_usd: Decimal, fee_usd: Decimal, share_mode: str
) -> Decimal:
    """Most shares we can buy so that round_pay(qty × price) + round_pay(fee) ≤ cash."""
    cash_usd = require_decimal(cash_usd, "cash_usd")
    price_usd = require_decimal(price_usd, "price_usd")
    fee_usd = require_decimal(fee_usd, "fee_usd")
    if price_usd <= 0:
        raise ValueError(f"price_usd must be > 0, got {price_usd}")
    if fee_usd < 0:
        raise ValueError(f"fee_usd must be ≥ 0, got {fee_usd}")
    available = cash_usd - round_pay(fee_usd)
    if available <= 0:
        return Decimal(0)
    step = Decimal(1) if share_mode == "whole" else SHARE_STEP
    quantity = round_shares_down(available / price_usd, share_mode)
    # Rounding the cost UP can push it a cent over; step down until it fits.
    while quantity > 0 and round_pay(quantity * price_usd) > available:
        quantity -= step
    return max(quantity, Decimal(0))
