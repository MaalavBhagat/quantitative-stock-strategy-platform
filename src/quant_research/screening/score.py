"""Quality score, "why" lines and Spearman correlation (Phase 7, Step 7.3 — research/SCREENING_METHOD.md v1).

Descriptive only — not a recommendation. Floats are fine here (D1).
"""

import statistics
from dataclasses import dataclass
from datetime import date
from typing import Any

from quant_research.screening import fundamentals as fu

# input name → (label in plain words, higher is better?)
INPUTS: dict[str, tuple[str, bool]] = {
    "return_on_assets": ("return on assets", True),
    "fcf_margin": ("free-cash-flow margin", True),
    "liabilities_to_assets": ("liabilities ÷ assets", False),
    "current_ratio": ("current ratio", True),
    "eps_growth_stdev_5y": ("earnings steadiness", False),
}
MIN_INPUTS = 4


def average_ranks(values: list[float], higher_is_better: bool) -> list[float]:
    """Place of each value (1 = best); ties share the average of the places they occupy."""
    order = sorted(range(len(values)), key=lambda i: values[i], reverse=higher_is_better)
    places = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            places[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return places


def rank_subscores(values: dict[str, float | None], higher_is_better: bool) -> dict[str, float]:
    """best = 1.0, worst = 0.0 among companies WITH a value; (n − place) ÷ (n − 1); one company → 0.5."""
    have = {k: v for k, v in values.items() if v is not None}
    if not have:
        return {}
    if len(have) == 1:
        return dict.fromkeys(have, 0.5)
    names = list(have)
    places = average_ranks([have[k] for k in names], higher_is_better)
    n = len(names)
    return {k: (n - p) / (n - 1) for k, p in zip(names, places, strict=True)}


@dataclass(frozen=True)
class Score:
    company: str
    quality: float | None  # None = NOT SCORED
    subscores: dict[str, float]
    missing: dict[str, str]  # input → why
    why: str


def why_line(company: str, subs: dict[str, float], missing: dict[str, str]) -> str:
    """Plain-English summary built only from the sub-scores (never typed by hand)."""
    if len(subs) < MIN_INPUTS:
        return (
            f"{company}: NOT SCORED — only {len(subs)} of 5 inputs (missing: "
            + "; ".join(f"{INPUTS[k][0]} {v}" for k, v in missing.items())
            + ")."
        )
    ordered = sorted(subs.items(), key=lambda kv: (-kv[1], list(INPUTS).index(kv[0])))
    best, worst = ordered[0], ordered[-1]
    if best[1] == worst[1]:
        line = f"{company}: the same on every input used ({best[1]:.2f})"
        if missing:
            line += "; left out: " + "; ".join(f"{INPUTS[k][0]} {v}" for k, v in missing.items())
        return line + "."
    line = (
        f"{company}: strongest on {INPUTS[best[0]][0]} ({best[1]:.2f}), "
        f"weakest on {INPUTS[worst[0]][0]} ({worst[1]:.2f})"
    )
    if missing:
        line += "; left out: " + "; ".join(f"{INPUTS[k][0]} {v}" for k, v in missing.items())
    return line + "."


def quality_scores(inputs: dict[str, dict[str, Any]]) -> dict[str, Score]:
    """inputs[company][input] = fu.Indicator (or None if no 10-K). MISSING / CONFLICT count as missing."""
    values: dict[str, dict[str, float | None]] = {k: {} for k in INPUTS}
    missing: dict[str, dict[str, str]] = {c: {} for c in inputs}
    for c, ind in inputs.items():
        for k in INPUTS:
            i = ind.get(k)
            ok = i is not None and i.status in (fu.FOUND, fu.FALLBACK) and i.value is not None
            values[k][c] = i.value if ok else None
            if not ok:
                missing[c][k] = "no 10-K" if i is None else i.status
    subs: dict[str, dict[str, float]] = {c: {} for c in inputs}
    for k, (_, higher) in INPUTS.items():
        for c, s in rank_subscores(values[k], higher).items():
            subs[c][k] = s
    out = {}
    for c in inputs:
        q = statistics.mean(subs[c].values()) if len(subs[c]) >= MIN_INPUTS else None
        out[c] = Score(c, q, subs[c], missing[c], why_line(c, subs[c], missing[c]))
    return out


def latest_10k_before(companyfacts: dict[str, Any], as_of: date) -> fu.FiscalYear | None:
    """The latest original 10-K filed STRICTLY before the as-of date (point-in-time)."""
    before = [fy for fy in fu.fiscal_years(companyfacts) if fy.filed < as_of]
    return max(before, key=lambda fy: fy.filed) if before else None


def indicators_on(
    companyfacts: dict[str, Any], as_of: date
) -> tuple[fu.FiscalYear | None, dict[str, fu.Indicator]]:
    """Indicators of the latest 10-K filed before `as_of`, with every value as known before `as_of`."""
    fy = latest_10k_before(companyfacts, as_of)
    if fy is None:
        return None, {}
    return fy, fu.indicators_as_of(companyfacts, fy.end, as_of)


def spearman(xs: list[float], ys: list[float]) -> float:
    """Spearman rank correlation = Pearson correlation of the average ranks (ties handled)."""
    if len(xs) != len(ys) or len(xs) < 3:
        raise ValueError("need two lists of equal length ≥ 3")
    rx, ry = average_ranks(xs, False), average_ranks(ys, False)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    if den == 0:
        raise ValueError("a list has no variation — correlation undefined")
    return num / den
