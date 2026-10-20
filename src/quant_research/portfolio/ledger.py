"""The portfolio ledger: cash, positions and an append-only audit trail (Phase 3, Steps 3.1–3.6).

The ledger only RECORDS trades it is told about — it never decides prices, fees or timing.
Rules (PROJECT_GUIDE §4): Decimal only (D1); cash rounded to cents against us (D2); shares
bought rounded down to 6 dp in fractional mode (D3). Profit/loss uses AVERAGE COST, with buy fees
in the cost basis and sell fees taken from proceeds [ASSUMPTION — no tax modelling].
A refused trade raises an error and changes nothing.
Daily event order (PROJECT_GUIDE §4): split → dividend → trades. The ledger refuses a split after a
dividend or trade on the same day for that ticker, and a dividend after a trade.
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
from quant_research.ratios import nearest_simple_ratio

logger = logging.getLogger(__name__)

ShareMode = Literal["whole", "fractional"]
EntryType = Literal["START", "BUY", "SELL", "DIVIDEND", "SPLIT"]
STAKE_MIN_ORDER_USD = Decimal(10)  # BROKER_FEES §4 [OFFICIAL], excluding brokerage
US_WITHHOLDING_W8BEN = Decimal("0.15")  # VERIFIED 2026-10-20, link in EXPERIMENT_PLAN §1
MIN_DIVIDEND_CREDIT_USD = Decimal("0.01")  # BROKER_FEES §4: amounts below a minimum not credited


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
    withholding_usd: Decimal | None = None  # dividends only
    ratio: Decimal | None = None  # splits only (snapped ratio)
    note: str | None = None


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
        self._div_gross = Decimal("0.00")
        self._withholding = Decimal("0.00")
        self._div_net = Decimal("0.00")
        self._applied_dividends: set[tuple[str, date]] = set()
        self._applied_splits: set[tuple[str, date]] = set()
        self._events: dict[tuple[str, date], set[str]] = {}
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
    def dividends_gross_usd(self) -> Decimal:
        """Dividends credited, before withholding tax."""
        return self._div_gross

    @property
    def withholding_usd(self) -> Decimal:
        return self._withholding

    @property
    def dividends_net_usd(self) -> Decimal:
        """Dividend cash actually credited (gross − withholding)."""
        return self._div_net

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
        self._events.setdefault((t, when), set()).add("trade")
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
        self._events.setdefault((t, when), set()).add("trade")
        entry = LedgerEntry(
            when, "SELL", t, qty, price, fee_charged, proceeds, before, self._cash, pnl
        )
        self._entries.append(entry)
        logger.debug("SELL %s %s @ %s, fee %s, P&L %s", qty, t, price, fee, pnl)
        return entry

    # ---------- corporate actions (Steps 3.5, 3.6) ----------
    def _check_ticker(self, ticker: str) -> str:
        if not isinstance(ticker, str) or not ticker.strip():
            raise ValueError("ticker must be a non-empty string")
        return ticker.strip().upper()

    def apply_dividend(
        self,
        ex_date: date,
        ticker: str,
        amount_per_share_usd: Decimal | int | str,
        withholding_rate: Decimal | int | str = US_WITHHOLDING_W8BEN,
    ) -> LedgerEntry | None:
        """Credit a dividend to shares held at the close BEFORE ex_date (DATA_SOURCES §7 row 6).

        Must be called before any trade in `ticker` on ex_date. Cash is credited on the ex-date
        [ASSUMPTION — no pay date in the data]. gross rounded DOWN, withholding rounded UP,
        net = gross − withholding; net below US$0.01 is not credited (logged with a note).
        Dividends never change the cost basis. Returns None if no shares are held.
        """
        self._check_date(ex_date)
        t = self._check_ticker(ticker)
        amount = require_decimal(amount_per_share_usd, "amount_per_share_usd")
        rate = require_decimal(withholding_rate, "withholding_rate")
        if amount <= 0:
            raise ValueError(f"amount_per_share_usd must be > 0, got {amount}")
        if not 0 <= rate < 1:
            raise ValueError(f"withholding_rate must be in [0, 1), got {rate}")
        if (t, ex_date) in self._applied_dividends:
            raise LedgerError(f"dividend for {t} on {ex_date} was already applied")
        if "trade" in self._events.get((t, ex_date), set()):
            raise LedgerError(
                f"a {t} trade is already logged on {ex_date} — apply the dividend BEFORE trades "
                "(entitlement = shares held at the previous close)"
            )
        self._applied_dividends.add((t, ex_date))
        self._events.setdefault((t, ex_date), set()).add("dividend")
        self._last_date = ex_date
        held = self._quantity.get(t, Decimal(0))
        if held == 0:
            logger.debug("dividend %s %s: no shares held — nothing credited", t, ex_date)
            return None
        gross_exact = held * amount
        gross = round_receive(gross_exact)
        withholding = round_pay(gross_exact * rate)
        net = gross - withholding
        before = self._cash
        if net < MIN_DIVIDEND_CREDIT_USD:
            entry = LedgerEntry(
                ex_date, "DIVIDEND", t, held, amount, Decimal(0), gross, before, before,
                withholding_usd=withholding,
                note=f"net US${net} below US${MIN_DIVIDEND_CREDIT_USD} — not credited",
            )  # fmt: skip
            self._entries.append(entry)
            logger.info("dividend %s %s too small (net %s) — not credited", t, ex_date, net)
            return entry
        self._cash += net
        self._div_gross += gross
        self._withholding += withholding
        self._div_net += net
        entry = LedgerEntry(
            ex_date, "DIVIDEND", t, held, amount, Decimal(0), gross, before, self._cash,
            withholding_usd=withholding,
        )  # fmt: skip
        self._entries.append(entry)
        return entry

    def apply_split(
        self, when: date, ticker: str, ratio: Decimal | int | str
    ) -> LedgerEntry | None:
        """Apply a split at the START of `when` (before dividends and trades).

        The ratio is snapped to the nearest realistic ratio (quant_research.ratios, same as data
        validation: 7.000007 → 7). Shares × ratio; cost basis and cash unchanged.
        Whole mode: a result that is not a whole number raises NotImplementedError (cash-in-lieu
        not modelled). Fractional mode: rounded DOWN to 6 dp, dropped fraction noted.
        Returns None if no shares are held.
        """
        self._check_date(when)
        t = self._check_ticker(ticker)
        raw_ratio = require_decimal(ratio, "ratio")
        if raw_ratio <= 0:
            raise ValueError(f"split ratio must be > 0, got {raw_ratio}")
        if (t, when) in self._applied_splits:
            raise LedgerError(f"split for {t} on {when} was already applied")
        if self._events.get((t, when), set()) & {"dividend", "trade"}:
            raise LedgerError(
                f"{t} already has a dividend or trade on {when} — apply the split FIRST "
                "(order: split → dividend → trades)"
            )
        snapped = nearest_simple_ratio(raw_ratio)
        num, den = Decimal(snapped.numerator), Decimal(snapped.denominator)
        held = self._quantity.get(t, Decimal(0))
        note = None
        if held > 0:
            if self.share_mode == "whole":
                if (held * num) % den != 0:
                    raise NotImplementedError(
                        f"cash-in-lieu not modelled: {held} {t} × {snapped} is not a whole number"
                    )
                new_qty = held * num / den
            else:
                exact = held * num / den
                new_qty = round_shares_down(exact, "fractional")
                if new_qty != exact:
                    note = f"fraction dropped: {exact - new_qty} shares (rounded down to 6 dp)"
        self._applied_splits.add((t, when))
        self._events.setdefault((t, when), set()).add("split")
        self._last_date = when
        if held == 0:
            logger.debug("split %s %s: no shares held — nothing to do", t, when)
            return None
        self._quantity[t] = new_qty
        ratio_value = num / den
        detail = f"{held} → {new_qty} shares (ratio {snapped.numerator}:{snapped.denominator}"
        detail += f", data factor {raw_ratio})"
        entry = LedgerEntry(
            when, "SPLIT", t, new_qty, Decimal(0), Decimal(0), Decimal(0), self._cash, self._cash,
            ratio=ratio_value, note=f"{detail}; {note}" if note else detail,
        )  # fmt: skip
        self._entries.append(entry)
        return entry
