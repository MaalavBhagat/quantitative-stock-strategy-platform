"""Transaction cost model (Phase 3, Step 3.4): brokerage, spread + slippage, currency conversion.

Pure functions — they calculate costs and never touch the ledger. Decimal only (D1); amounts
we pay round UP, amounts we receive round DOWN (D2). Every number lives in COST_TABLE below with
its source (copied from research/BROKER_FEES.md) or the label [ASSUMPTION].
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from quant_research.portfolio.money import require_decimal, round_pay, round_receive

STAKE_SRC = "https://hellostake.com/au/pricing (VERIFIED 2026-10-17)"
STAKE_FX_OUT_SRC = (
    "https://hellostake.com/support/funding-and-withdrawal/withdrawal/26014595952153 "
    "(VERIFIED 2026-10-20)"
)
IBKR_SRC = "https://www.interactivebrokers.com.au/en/pricing/commissions-home.php"
COMMSEC_SRC = "https://static.commsec.com.au/support/rates-and-fees.html"
SPREAD_SRC = "[ASSUMPTION] no free historical spread data (SMALL_ACCOUNT_FEASIBILITY.md)"


@dataclass(frozen=True)
class CostParam:
    value: Decimal
    unit: str
    source: str


# ---------- the ONE config table ----------
COST_TABLE: dict[str, CostParam] = {
    # Stake (MAIN case)
    "stake.flat_fee_usd": CostParam(Decimal("3.00"), "USD per trade", STAKE_SRC),
    "stake.flat_up_to_usd": CostParam(Decimal(30000), "USD trade value", STAKE_SRC),
    "stake.pct_above": CostParam(Decimal("0.0001"), "of trade value (0.01%)", STAKE_SRC),
    "stake.fx_rate": CostParam(Decimal("0.0055"), "of amount converted (0.55%)", STAKE_SRC),
    "stake.fx_rate_withdrawal": CostParam(Decimal("0.0055"), "USD→AUD (0.55%)", STAKE_FX_OUT_SRC),
    # Interactive Brokers, Fixed pricing (LOW case)
    "ibkr.per_share_usd": CostParam(Decimal("0.005"), "USD per share", IBKR_SRC),
    "ibkr.min_usd": CostParam(Decimal("1.00"), "USD per trade", IBKR_SRC),
    "ibkr.max_pct": CostParam(Decimal("0.01"), "of trade value (1%)", IBKR_SRC),
    "ibkr.fx_rate": CostParam(Decimal("0.00002"), "of amount (~0.002%, manual)", IBKR_SRC),
    "ibkr.fx_min_usd": CostParam(Decimal("2.00"), "USD per conversion", IBKR_SRC),
    # CommSec standard (HIGH case) — converts AUD↔USD on EVERY trade
    "commsec.min_usd": CostParam(Decimal("5.00"), "USD per trade", COMMSEC_SRC),
    "commsec.pct": CostParam(Decimal("0.0012"), "of trade value (0.12%)", COMMSEC_SRC),
    "commsec.fx_rate": CostParam(
        Decimal("0.0055"), "of trade value per trade (0.55%)", COMMSEC_SRC
    ),
    # Spread + slippage per side
    "spread.tight": CostParam(Decimal("0.0002"), "per side (0.02%)", SPREAD_SRC),
    "spread.normal": CostParam(Decimal("0.0005"), "per side (0.05%)", SPREAD_SRC),
    "spread.wide": CostParam(Decimal("0.0010"), "per side (0.10%)", SPREAD_SRC),
}

Broker = Literal["stake", "ibkr_fixed", "commsec_standard"]
SpreadLevel = Literal["tight", "normal", "wide"]
Side = Literal["buy", "sell"]
BROKERS: tuple[str, ...] = ("stake", "ibkr_fixed", "commsec_standard")


def cost(key: str) -> Decimal:
    """Value from COST_TABLE (KeyError names the missing key)."""
    return COST_TABLE[key].value


@dataclass(frozen=True)
class FeeBreakdown:
    brokerage_usd: Decimal
    fx_usd: Decimal  # per-trade FX (CommSec only); 0 for brokers that hold USD
    total_usd: Decimal


@dataclass(frozen=True)
class SpreadFill:
    fill_price_usd: Decimal
    spread_cost_usd: Decimal  # |fill − reference| × quantity (exact, not rounded)


@dataclass(frozen=True)
class FxResult:
    amount_in: Decimal
    amount_out: Decimal
    fee_usd: Decimal
    usd_per_aud: Decimal


def _positive(value: object, name: str) -> Decimal:
    d = require_decimal(value, name)
    if d <= 0:
        raise ValueError(f"{name} must be > 0, got {d}")
    return d


def fee_usd(broker: str, trade_value_usd: Decimal, quantity: Decimal) -> FeeBreakdown:
    """Brokerage (and per-trade FX for CommSec) for ONE trade, each part rounded up to the cent."""
    value = _positive(trade_value_usd, "trade_value_usd")
    qty = _positive(quantity, "quantity")
    fx = Decimal(0)
    if broker == "stake":
        if value <= cost("stake.flat_up_to_usd"):
            brokerage = cost("stake.flat_fee_usd")
        else:
            brokerage = value * cost("stake.pct_above")
    elif broker == "ibkr_fixed":
        per_share = qty * cost("ibkr.per_share_usd")
        brokerage = min(max(per_share, cost("ibkr.min_usd")), value * cost("ibkr.max_pct"))
    elif broker == "commsec_standard":
        brokerage = max(cost("commsec.min_usd"), value * cost("commsec.pct"))
        fx = value * cost("commsec.fx_rate")
    else:
        raise ValueError(f"unknown broker {broker!r} — choose one of {', '.join(BROKERS)}")
    brokerage, fx = round_pay(brokerage), round_pay(fx)
    return FeeBreakdown(brokerage, fx, brokerage + fx)


def apply_spread(
    reference_price_usd: Decimal, side: Side, level: SpreadLevel, quantity: Decimal
) -> SpreadFill:
    """Fill price after spread + slippage: buy pays more, sell receives less."""
    ref = _positive(reference_price_usd, "reference_price_usd")
    qty = _positive(quantity, "quantity")
    if level not in ("tight", "normal", "wide"):
        raise ValueError(f"spread level must be tight / normal / wide, got {level!r}")
    s = cost(f"spread.{level}")
    if side == "buy":
        fill = ref * (1 + s)
    elif side == "sell":
        fill = ref * (1 - s)
    else:
        raise ValueError(f"side must be 'buy' or 'sell', got {side!r}")
    return SpreadFill(fill, abs(fill - ref) * qty)


def fx_fee_settings(broker: str, direction: Literal["in", "out"] = "in") -> tuple[Decimal, Decimal]:
    """(fee_rate, min_fee_usd) for converting at the start ('in') or end ('out'). CommSec: 0 (per-trade FX)."""
    if broker == "stake":
        rate = cost("stake.fx_rate") if direction == "in" else cost("stake.fx_rate_withdrawal")
        return rate, Decimal(0)
    if broker == "ibkr_fixed":
        return cost("ibkr.fx_rate"), cost("ibkr.fx_min_usd")
    if broker == "commsec_standard":
        # CommSec converts AUD↔USD inside EVERY trade (fee_usd charges 0.55% FX per trade), so there is no separate
        # start/end conversion fee — charging both would count the FX twice on the first buy and the last sale
        # (bug fixed 2026-10-25 before any validation run, Goggy; PREREGISTRATION §9).
        return Decimal(0), Decimal(0)
    raise ValueError(f"unknown broker {broker!r} — choose one of {', '.join(BROKERS)}")


def aud_to_usd(
    amount_aud: Decimal, usd_per_aud: Decimal, fee_rate: Decimal, min_fee_usd: Decimal = Decimal(0)
) -> FxResult:
    """AUD → USD. Fee in USD = max(rate × USD amount, minimum), rounded UP; USD out rounded DOWN.

    The exchange rate is always passed in (never hard-coded).
    """
    aud = _positive(amount_aud, "amount_aud")
    rate = _positive(usd_per_aud, "usd_per_aud")
    fee_rate = require_decimal(fee_rate, "fee_rate")
    min_fee = require_decimal(min_fee_usd, "min_fee_usd")
    gross_usd = aud * rate
    fee = round_pay(max(gross_usd * fee_rate, min_fee))
    return FxResult(aud, round_receive(gross_usd - fee), fee, rate)


def usd_to_aud(
    amount_usd: Decimal, usd_per_aud: Decimal, fee_rate: Decimal, min_fee_usd: Decimal = Decimal(0)
) -> FxResult:
    """USD → AUD. Fee in USD rounded UP is taken first; AUD out rounded DOWN."""
    usd = _positive(amount_usd, "amount_usd")
    rate = _positive(usd_per_aud, "usd_per_aud")
    fee_rate = require_decimal(fee_rate, "fee_rate")
    min_fee = require_decimal(min_fee_usd, "min_fee_usd")
    fee = round_pay(max(usd * fee_rate, min_fee))
    if fee >= usd:
        raise ValueError(f"conversion fee US${fee} is not less than the amount US${usd}")
    return FxResult(usd, round_receive((usd - fee) / rate), fee, rate)
