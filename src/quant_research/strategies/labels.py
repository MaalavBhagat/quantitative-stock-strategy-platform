"""Plain-English strategy names (Goggy's request 2026-10-28). DISPLAY ONLY.

The IDs (S0 … S4-S2, C1, C2, E1) stay unchanged in code, configs, run records and the pre-registrations; this one
table turns them into "Buy-and-hold (S0)" etc. for the dashboard, generated reports and exports.
"""

import re

# config strategy name → ID (the registry's names; a test checks every registry name is here)
IDS = {
    "s0_buy_and_hold": "S0",
    "s1_profit_target": "S1",
    "s2_pullback": "S2",
    "s3_mean_reversion": "S3",
    "s4_trend_s1": "S4-S1",
    "s4_trend_s2": "S4-S2",
    "c1_market_gate": "C1",
    "c2_market_gated_pullback": "C2",
    "e1_earnings_cooloff": "E1",
}
# ID → (display name, one-line explanation)
LABELS = {
    "S0": (
        "Buy-and-hold",
        "Buy on day 1 and keep it; dividends reinvested once cash reaches US$100.",
    ),
    "S1": (
        "Profit target",
        "Sell after the price rises X% above the buy price; buy back after it falls Y% below the sell price.",
    ),
    "S2": (
        "Pullback from peak",
        "Sell after an X% rise; buy back after a Y% fall from the highest price since selling.",
    ),
    "S3": (
        "Mean reversion",
        "Sell when the price is k standard deviations above its w-day average; buy back when it's k below.",
    ),
    "S4-S1": (
        "Trend filter + profit target",
        "S1, but never sell while the stock is in a strong uptrend (above a rising 200-day average).",
    ),
    "S4-S2": (
        "Trend filter + pullback",
        "S2, but never sell in a strong uptrend.",
    ),
    "C1": (
        "Market-trend gate",
        "Hold the stock only while SPY is above its rising 200-day average; otherwise sell and wait in cash.",
    ),
    "C2": (
        "Market-gated pullback",
        "Trend filter + pullback, but no buy-back while SPY is below its 200-day average.",
    ),
    "E1": (
        "Earnings cool-off",
        (
            "Trend filter + pullback, but ignore buy/sell signals for 2 trading days once an earnings "
            "filing becomes usable."
        ),
    ),
}
# longest first, so "S4-S1" is matched before "S1"
_ID_RE = re.compile(
    r"(?<![\w-])("
    + "|".join(re.escape(i) for i in sorted(LABELS, key=len, reverse=True))
    + r")(?![\w-])"
)


def name(strategy_id: str) -> str:
    return LABELS[strategy_id][0]


def explain(strategy_id: str) -> str:
    return LABELS[strategy_id][1]


def display(strategy_id: str) -> str:
    """'Buy-and-hold (S0)'."""
    return f"{name(strategy_id)} ({strategy_id})"


def of_config(strategy: str) -> str:
    """Config strategy name ('s4_trend_s2') → ID ('S4-S2')."""
    return IDS[strategy]


def _protect(text: str) -> tuple[str, dict[str, str]]:
    """Replace every already-named 'Name (ID)' by a placeholder so it is never named twice."""
    keep: dict[str, str] = {}
    for i, sid in enumerate(sorted(LABELS, key=len, reverse=True)):
        token = f"\x00{i}\x00"
        if display(sid) in text:
            text = text.replace(display(sid), token)
            keep[token] = display(sid)
    return text, keep


def bare_ids(text: str) -> list[str]:
    """IDs that appear WITHOUT their name ('S1' alone, not 'Profit target (S1)')."""
    stripped, _ = _protect(text)
    return _ID_RE.findall(stripped)


def name_ids(text: str) -> str:
    """Give every bare ID in a text its name: 'S1 lost' → 'Profit target (S1) lost'. Already-named IDs are kept."""
    stripped, keep = _protect(text)
    named = _ID_RE.sub(lambda m: display(m.group(1)), stripped)
    for token, original in keep.items():
        named = named.replace(token, original)
    return named
