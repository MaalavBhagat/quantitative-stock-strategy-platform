"""Shared chart colours (theme 2026-10-30): strategy burgundy and solid; buy-and-hold sage, thicker and dashed."""

import pytest

alt = pytest.importorskip("altair")

from quant_research.dashboard import chart_style as cs


def test_strategy_is_burgundy_and_buy_and_hold_is_dashed_sage_whatever_the_order():
    enc = cs.series_lines(
        ["Buy-and-hold (S0)", "Profit target (S1) X 2% / Y 2%"], "Buy-and-hold (S0)"
    )
    colour = enc["color"].to_dict()["scale"]
    assert colour["domain"] == ["Profit target (S1) X 2% / Y 2%", "Buy-and-hold (S0)"]
    assert colour["range"] == ["#590907", "#A5A79B"]
    assert enc["strokeDash"].to_dict()["scale"]["range"] == [[1, 0], [6, 4]]
    assert enc["strokeWidth"].to_dict()["scale"]["range"] == [2, 3.5]


def test_strategy_alone_and_extra_series():
    assert cs.series_lines(["Buy-and-hold (S0)"])["color"].to_dict()["scale"]["range"] == [
        "#590907"
    ]
    assert cs.extra_colours(["Cash", "Invested"], "part").to_dict()["scale"]["range"] == [
        "#6F7264",
        "#B8956A",
    ]


def test_dates_show_years_and_legend_labels_are_never_cut():
    assert cs.date_x().to_dict()["axis"]["format"] == "%b %Y"
    enc = cs.series_lines(["A very long strategy name (S4-S2) X 2% / Y 4%"])
    assert enc["color"].to_dict()["legend"]["labelLimit"] == 0
