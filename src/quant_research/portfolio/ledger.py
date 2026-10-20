"""The portfolio ledger: cash, positions and an append-only audit trail (Phase 3, Steps 3.1–3.3).

The ledger only RECORDS trades it is told about — it never decides prices, fees or timing.
Rules (PROJECT_GUIDE §4): Decimal only (D1); cash rounded to cents against us (D2); shares
bought rounded down to 6 dp in fractional mode (D3). Profit/loss uses AVERAGE COST, with buy fees
in the cost basis and sell fees taken from proceeds [ASSUMPTION — no tax modelling].
A refused trade raises an error and changes nothing.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from quant_research.portfolio.money import (
    CENT,
    SHARE_STEP,
    require_decimal,
    round_pay,
    round_receive,
    round_shares_down,
)

logger = logging.getLogger(__name__)

ShareMode = Literal["whole", "fractional"]
EntryType = Literal["START", "BUY", "SELL"]
STAKE_MIN_ORDER_USD = Decimal(10)  # BROKER_FEES §4 [OFFICIAL], excluding brokerage


class LedgerError(ValueError):
    """A trade was refused; the portfolio is unchanged."""


class InsufficientCashError(LedgerError):
    pass


class InsufficientSharesError(LedgerError):
    pass


@dataclass(frozen=True)
class LedgerEntry:
    """One immutable line of the audit trail."""

    date: date
    type: EntryType
    ticker: str | None
    quantity: Decimal
    price_usd: Decimal
    fee_usd: Decimal  # as charged (rounded up to the cent)
    gross_usd: Decimal  # quantity × price, rounded against us (buy: up, sell: down)
    cash_before_usd: Decimal
    cash_after_usd: Decimal
    realised_pnl_usd: Decimal | None = None  # sells only


@dataclass(frozen=True)
class Position:
    """Snapshot of one holding."""

    ticker: str
    quantity: Decimal
    cost_basis_usd: Decimal  # total cost of the shares still held, incl. buy fees

    @property
    def average_cost_usd(self) -> Decimal:
        """Cost per share (unrounded). Zero when nothing is held."""
        return self.cost_basis_usd / self.quantity if self.quantity else Decimal(0)


class Portfolio:
    """Cash + positions + audit trail for one simulated account (USD)."""

    def __init__(
        self,
        initial_cash_usd: Decimal | int | str,
        share_mode: ShareMode = "fractional",
        min_order_usd: Decimal | int | str | None = STAKE_MIN_ORDER_USD,
        start_date: date | None = None,
    ) -> None:
        if share_mode not in ("whole", "fractional"):
            raise ValueError(f"share_mode must be 'whole' or 'fractional', got {share_mode!r}")
        cash = require_decimal(initial_cash_usd, "initial_cash_usd")
        if cash < 0:
            raise ValueError(f"initial_cash_usd must be ≥ 0, got {cash}")
        if cash != cash.quantize(CENT):
            raise ValueError(f"initial_cash_usd must be whole cents, got {cash}")
        self.share_mode: ShareMode = share_mode
        self.min_order_usd = (
            None if min_order_usd is None else require_decimal(min_order_usd, "min_order_usd")
        )
        self.initial_cash_usd = cash
        self._cash = cash
        self._spent = Decimal("0.00")
        self._received = Decimal("0.00")
        self._fees = Decimal("0.00")
        self._realised = Decimal("0.00")
        self._quantity: dict[str, Decimal] = {}
        self._basis: dict[str, Decimal] = {}
        self._last_date: date | None = None
        self._entries: list[LedgerEntry] = []
        if start_date is not None:
            self._check_date(start_date)
            self._last_date = start_date
            self._entries.append(
                LedgerEntry(
                    start_date, "START", None, Decimal(0), Decimal(0), Decimal(0), cash,
                    Decimal(0), cash,
                )
            )  # fmt: skip

    # ---------- read-only views ----------
    @property
    def cash_usd(self) -> Decimal:
        return self._cash

    @property
    def total_spent_usd(self) -> Decimal:
        """Cash paid for shares (excluding fees)."""
        return self._spent

    @property
    def total_received_usd(self) -> Decimal:
        """Cash received from sales (before sell fees)."""
        return self._received

    @property
    def total_fees_usd(self) -> Decimal:
        return self._fees

    @property
    def realised_pnl_usd(self) -> Decimal:
        return self._realised

    @property
    def entries(self) -> tuple[LedgerEntry, ...]:
        """The audit trail (a tuple — it cannot be edited from outside)."""
        return tuple(self._entries)

    def position(self, ticker: str) -> Position:
        t = ticker.upper()
        return Position(t, self._quantity.get(t, Decimal(0)), self._basis.get(t, Decimal(0)))

    # ---------- validation helpers ----------
    def _check_date(self, when: date) -> None:
        if isinstance(when, datetime) or not isinstance(when, date):
            raise TypeError(f"date must be a datetime.date (no time), got {type(when).__name__}")
        if self._last_date is not None and when < self._last_date:
            raise LedgerError(f"date {when} is before the last ledger date {self._last_date}")

    def _check_trade_inputs(
        self, when: date, ticker: str, quantity: object, price_usd: object, fee_usd: object
    ) -> tuple[str, Decimal, Decimal, Decimal]:
        self._check_date(when)
        if not isinstance(ticker, str) or not ticker.strip():
            raise ValueError("ticker must be a non-empty string")
        qty = require_decimal(quantity, "quantity")
        price = require_decimal(price_usd, "price_usd")
        fee = require_decimal(fee_usd, "fee_usd")
        if qty <= 0:
            raise ValueError(f"quantity must be > 0, got {qty}")
        if price <= 0:
            raise ValueError(f"price_usd must be > 0, got {price}")
        if fee < 0:
            raise ValueError(f"fee_usd must be ≥ 0, got {fee}")
        if self.share_mode == "whole" and qty != qty.to_integral_value():
            raise ValueError(f"share_mode is 'whole' — quantity must be a whole number, got {qty}")
        return ticker.strip().upper(), qty, price, fee

    def _check_min_order(self, gross: Decimal, what: str) -> None:
        if self.min_order_usd is not None and gross < self.min_order_usd:
            raise LedgerError(
                f"{what} value US${gross} is below the minimum order US${self.min_order_usd}"
            )

    # ---------- trades ----------
    def buy(
        self,
        when: date,
        ticker: str,
        quantity: Decimal | int | str,
        price_usd: Decimal | int | str,
        fee_usd: Decimal | int | str,
    ) -> LedgerEntry:
        """Record a purchase. Fractional quantities are rounded DOWN to 6 dp (D3)."""
        t, qty, price, fee = self._check_trade_inputs(when, ticker, quantity, price_usd, fee_usd)
        qty = round_shares_down(qty, self.share_mode)
        if qty <= 0:
            raise LedgerError(f"quantity rounds down to 0 shares (minimum step {SHARE_STEP})")
        self._check_min_order(qty * price, "buy")
        cost = round_pay(qty * price)
        fee_charged = round_pay(fee)
        total = cost + fee_charged
        if total > self._cash:
            raise InsufficientCashError(
                f"buy {qty} {t} @ US${price} needs US${cost} + fee US${fee_charged} = US${total}, "
                f"but cash is only US${self._cash} (short by US${total - self._cash})"
            )
        before = self._cash
        self._cash -= total
        self._spent += cost
        self._fees += fee_charged
        self._quantity[t] = self._quantity.get(t, Decimal(0)) + qty
        self._basis[t] = self._basis.get(t, Decimal(0)) + total
        self._last_date = when
        entry = LedgerEntry(when, "BUY", t, qty, price, fee_charged, cost, before, self._cash)
        self._entries.append(entry)
        logger.debug("BUY %s %s @ %s, fee %s, cash %s → %s", qty, t, price, fee, before, self._cash)
        return entry

    def sell(
        self,
        when: date,
        ticker: str,
        quantity: Decimal | int | str,
        price_usd: Decimal | int | str,
        fee_usd: Decimal | int | str,
    ) -> LedgerEntry:
        """Record a sale. Realised P&L = (proceeds − fee) − average cost of the shares sold."""
        t, qty, price, fee = self._check_trade_inputs(when, ticker, quantity, price_usd, fee_usd)
        if qty != qty.quantize(SHARE_STEP):
            raise ValueError(f"sell quantity has more than 6 decimal places: {qty}")
        held = self._quantity.get(t, Decimal(0))
        if qty > held:
            raise InsufficientSharesError(
                f"sell {qty} {t} but only {held} held (short by {qty - held})"
            )
        closing = qty == held
        if not closing:  # selling the whole position is allowed below the minimum [ASSUMPTION]
            self._check_min_order(qty * price, "sell")
        proceeds = round_receive(qty * price)
        fee_charged = round_pay(fee)
        net = proceeds - fee_charged
        if self._cash + net < 0:
            raise InsufficientCashError(
                f"sell fee US${fee_charged} exceeds proceeds US${proceeds} and cash "
                f"US${self._cash} cannot cover the difference"
            )
        basis = self._basis[t]
        basis_sold = basis if closing else basis * qty / held
        pnl = net - basis_sold
        before = self._cash
        self._cash += net
        self._received += proceeds
        self._fees += fee_charged
        self._realised += pnl
        self._quantity[t] = held - qty
        self._basis[t] = Decimal(0) if closing else basis - basis_sold
        self._last_date = when
        entry = LedgerEntry(
            when, "SELL", t, qty, price, fee_charged, proceeds, before, self._cash, pnl
        )
        self._entries.append(entry)
        logger.debug("SELL %s %s @ %s, fee %s, P&L %s", qty, t, price, fee, pnl)
        return entry
