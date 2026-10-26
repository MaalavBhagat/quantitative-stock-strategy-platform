"""Tests for quant_research.screening.score — hand-checked ranks, the ≥4-of-5 rule, as-of filtering, Spearman."""

import json
from datetime import date
from pathlib import Path

import pytest

from quant_research.data.sec import trim_companyfacts
from quant_research.screening import fundamentals as fu
from quant_research.screening.score import (
    average_ranks,
    indicators_on,
    latest_10k_before,
    quality_scores,
    rank_subscores,
    spearman,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "sec_companyfacts_sample.json"


def ind(value, status=fu.FOUND):
    return fu.Indicator("x", status, value)


def company(roa, fcf, la, cr, eps):
    vals = dict(
        zip(
            [
                "return_on_assets",
                "fcf_margin",
                "liabilities_to_assets",
                "current_ratio",
                "eps_growth_stdev_5y",
            ],
            [roa, fcf, la, cr, eps],
            strict=True,
        )
    )
    return {k: (v if isinstance(v, fu.Indicator) else ind(v)) for k, v in vals.items()}


def test_average_ranks_ties():
    # higher better: 0.3 → 1; two 0.2 share places 2–3 → 2.5; 0.1 → 4
    assert average_ranks([0.2, 0.3, 0.2, 0.1], higher_is_better=True) == [2.5, 1.0, 2.5, 4.0]


def test_rank_subscores_best_one_worst_zero_with_ties_and_missing():
    s = rank_subscores({"A": 0.2, "B": 0.3, "C": 0.2, "D": 0.1, "E": None}, higher_is_better=True)
    # n = 4 (E has no value): (4 − place) ÷ 3 → B 1.0, A and C (4 − 2.5)/3 = 0.5, D 0.0
    assert s == pytest.approx({"A": 0.5, "B": 1.0, "C": 0.5, "D": 0.0})
    assert rank_subscores({"A": 0.4, "B": 0.9}, higher_is_better=False) == {
        "A": 1.0,
        "B": 0.0,
    }  # lower better
    assert rank_subscores({"A": 0.4, "B": None}, True) == {"A": 0.5}  # one company → neutral
    assert rank_subscores({"A": None}, True) == {}


def test_quality_score_average_and_four_of_five_rule():
    scores = quality_scores(
        {
            "A": company(0.2, 0.3, 0.5, 2.0, 0.1),  # best on everything
            "B": company(0.1, 0.1, 0.7, 1.0, 0.4),  # worst on everything
            "C": company(0.15, ind(None, fu.CONFLICT), 0.6, 1.5, 0.2),  # 4 inputs: middle on each
            "D": company(0.15, ind(None, fu.MISSING), ind(None, fu.MISSING), 1.5, 0.2),  # 3 inputs
        }
    )
    assert scores["A"].quality == pytest.approx(1.0)
    assert scores["B"].quality == pytest.approx(0.0)
    # C: ROA 0.15 ties with D among 4 → places 2.5 → 0.5; FCF missing; L/A among A,B,C → 0.5; CR ties D → 0.5; EPS 0.5
    assert scores["C"].quality == pytest.approx(0.5)
    assert scores["C"].missing == {"fcf_margin": fu.CONFLICT}
    assert scores["D"].quality is None
    assert "NOT SCORED" in scores["D"].why and "free-cash-flow margin MISSING" in scores["D"].why
    assert scores["A"].why == "A: the same on every input used (1.00)."


def test_why_line_names_strongest_weakest_and_left_out():
    scores = quality_scores(
        {
            "A": company(0.2, 0.1, 0.5, 2.0, ind(None, fu.MISSING)),
            "B": company(0.1, 0.3, 0.7, 1.0, 0.4),
        }
    )
    assert scores["A"].why == (
        "A: strongest on return on assets (1.00), weakest on free-cash-flow margin (0.00); "
        "left out: earnings steadiness MISSING."
    )


def test_no_10k_counts_as_missing():
    scores = quality_scores({"A": {}, "B": company(0.1, 0.3, 0.7, 1.0, 0.4)})
    assert scores["A"].quality is None and set(scores["A"].missing.values()) == {"no 10-K"}


# ---------- point-in-time as-of filtering ----------
@pytest.fixture
def cf():
    trimmed, _ = trim_companyfacts(json.loads(FIXTURE.read_text()))
    return trimmed


def test_latest_10k_strictly_before_as_of(cf):
    # fixture 10-Ks: A16 filed 2017-02-17 … A19 filed 2020-02-14 (min_facts default 5 → only A19 counts)
    assert latest_10k_before(cf, date(2020, 2, 14)) is None  # filed ON the as-of date → not usable
    fy = latest_10k_before(cf, date(2020, 2, 15))
    assert fy is not None and fy.accn == "A19"
    assert latest_10k_before(cf, date(2019, 12, 31)) is None


def test_indicators_on_uses_values_known_before_as_of(cf):
    fy, ind_ = indicators_on(cf, date(2020, 12, 31))
    assert fy.end == date(2019, 12, 31)
    assert ind_["net_margin"].value == pytest.approx(100 / 1000)
    assert indicators_on(cf, date(2019, 12, 31)) == (None, {})


# ---------- Spearman ----------
def test_spearman_hand_checked():
    # x ranks 1..5; y = 2, 1, 4, 3, 5 → d = −1, 1, −1, 1, 0 → Σd² = 4 → 1 − 6·4/(5·24) = 0.8
    assert spearman([10, 20, 30, 40, 50], [2, 1, 4, 3, 5]) == pytest.approx(0.8)
    assert spearman([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)


def test_spearman_with_ties_is_pearson_of_average_ranks():
    # x ranks 1, 2.5, 2.5, 4; y ranks 1, 2, 3, 4 → Pearson: cov 2.5/… = 0.9486833
    assert spearman([1, 2, 2, 3], [1, 2, 3, 4]) == pytest.approx(0.9486833, rel=1e-6)


def test_spearman_refuses_too_few_or_constant():
    with pytest.raises(ValueError):
        spearman([1, 2], [1, 2])
    with pytest.raises(ValueError, match="no variation"):
        spearman([1, 1, 1], [1, 2, 3])
