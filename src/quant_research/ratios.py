"""Split ratios shared by data validation and the ledger (one function, no copies)."""

from decimal import Decimal
from fractions import Fraction

# Ratios real splits use: n-for-1 and 1-for-n (n ≤ 100), and small pairs like 3:2 (both ≤ 10).
SIMPLE_RATIOS = sorted(
    {Fraction(n, 1) for n in range(1, 101)}
    | {Fraction(1, n) for n in range(1, 101)}
    | {Fraction(p, q) for p in range(1, 11) for q in range(1, 11)}
)


def nearest_simple_ratio(factor: float | Decimal | Fraction) -> Fraction:
    """Closest realistic split ratio, e.g. 7.000007 → 7/1, 1.5 → 3/2, 0.25 → 1/4."""
    value = float(factor)
    if not value > 0:
        raise ValueError(f"split factor must be > 0, got {factor}")
    return min(SIMPLE_RATIOS, key=lambda ratio: abs(value - float(ratio)) / float(ratio))
