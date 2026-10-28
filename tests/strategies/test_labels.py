"""Plain-English strategy names (display only) — strategies/labels.py."""

from quant_research.strategies import labels
from quant_research.strategies.registry import STRATEGY_NAMES


def test_every_registry_strategy_has_a_label():
    assert set(STRATEGY_NAMES) <= set(labels.IDS)
    for sid in labels.IDS.values():
        name, explanation = labels.LABELS[sid]
        assert name and explanation


def test_table_as_agreed_2026_10_28():
    assert labels.display("S0") == "Buy-and-hold (S0)"
    assert labels.display("S4-S2") == "Trend filter + pullback (S4-S2)"
    assert labels.display("C1") == "Market-trend gate (C1)"
    assert labels.display("C2") == "Market-gated pullback (C2)"
    assert labels.display("E1") == "Earnings cool-off (E1)"
    assert labels.explain("S2") == (
        "Sell after an X% rise; buy back after a Y% fall from the highest price since selling."
    )


def test_name_ids_names_bare_ids_once():
    text = "| S1 | lost · S4-S2 beat S0 · Buy-and-hold (S0) stays · S1/S2"
    named = labels.name_ids(text)
    assert named == (
        "| Profit target (S1) | lost · Trend filter + pullback (S4-S2) beat Buy-and-hold (S0) · "
        "Buy-and-hold (S0) stays · Profit target (S1)/Pullback from peak (S2)"
    )
    assert labels.bare_ids(text) == ["S1", "S4-S2", "S0", "S1", "S2"]
    assert labels.bare_ids(named) == []
    assert labels.name_ids(named) == named  # never named twice


def test_ids_inside_words_are_not_ids():
    # run ids, file names and other words are left alone
    assert labels.bare_ids("val_main_s4s2_aapl · CS1 · S10 · S4") == []
