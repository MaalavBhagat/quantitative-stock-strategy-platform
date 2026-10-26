"""Tests for quant_research.screening.fundamentals — synthetic XBRL-like facts, hand-calculated answers."""

import copy
import json
import math
from datetime import date
from pathlib import Path

import pytest

from quant_research.data.sec import trim_companyfacts
from quant_research.screening.fundamentals import (
    CONFLICT,
    FALLBACK,
    FOUND,
    MISSING,
    NET_INCOME,
    REVENUE,
    concept_as_of,
    eps_growth_stdev,
    facts_for,
    fiscal_years,
    indicators_as_of,
    value_as_of,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "sec_companyfacts_sample.json"
FY19 = date(2019, 12, 31)
FILED19 = date(2020, 2, 14)  # A19 (the FY2019 10-K) filed on this day
NEXT_DAY = date(2020, 2, 15)


@pytest.fixture
def cf() -> dict:
    trimmed, _ = trim_companyfacts(json.loads(FIXTURE.read_text()))
    return trimmed


def usgaap(cf: dict) -> dict:
    return cf["facts"]["us-gaap"]


# ---------- point-in-time ----------
def test_fact_filed_on_day_t_is_not_usable_on_t(cf):
    facts = facts_for(cf, "Revenues", "USD")
    assert value_as_of(facts, FY19, FILED19, instant=False).status == MISSING
    on_next = value_as_of(facts, FY19, NEXT_DAY, instant=False)
    assert on_next.status == FOUND and on_next.fact.val == 1000 and on_next.fact.filed == FILED19


def test_restatement_used_only_from_the_later_filing_date(cf):
    facts = facts_for(cf, "NetIncomeLoss", "USD")
    fy18 = date(2018, 12, 31)
    # FY2018 net income: 80 in A18 (filed 2019-02-15), restated to 85 in A19 (filed 2020-02-14)
    assert value_as_of(facts, fy18, date(2019, 2, 15), False).status == MISSING  # not yet public
    assert value_as_of(facts, fy18, date(2019, 2, 16), False).fact.val == 80
    assert (
        value_as_of(facts, fy18, FILED19, False).fact.val == 80
    )  # restatement filed that day: not yet usable
    assert value_as_of(facts, fy18, NEXT_DAY, False).fact.val == 85


def test_quarterly_facts_are_ignored(cf):
    facts = facts_for(cf, "Revenues", "USD")
    assert value_as_of(facts, date(2020, 3, 31), date(2020, 12, 31), False).status == MISSING


def test_same_day_different_values_is_a_conflict_not_a_guess(cf):
    rows = usgaap(cf)["Revenues"]["units"]["USD"]
    rows.append({**rows[2], "val": 999, "accn": "A19X"})
    comp = concept_as_of(cf, REVENUE, FY19, NEXT_DAY)
    assert comp.status == CONFLICT and comp.value is None
    assert indicators_as_of(cf, FY19, NEXT_DAY)["net_margin"].status == CONFLICT


def test_trimmed_data_never_contains_the_2021_filing(cf):
    assert (
        value_as_of(
            facts_for(cf, "NetIncomeLoss", "USD"), date(2020, 12, 31), date(2030, 1, 1), False
        ).status
        == MISSING
    )


# ---------- tag mapping + fallbacks ----------
def test_fallback_tag_is_used_and_labelled(cf):
    usgaap(cf)["SalesRevenueNet"] = usgaap(cf).pop("Revenues")  # company uses an older tag
    comp = concept_as_of(cf, REVENUE, FY19, NEXT_DAY)
    assert comp.status == FALLBACK and comp.value == 1000 and comp.note == "SalesRevenueNet"
    assert indicators_as_of(cf, FY19, NEXT_DAY)["net_margin"].status == FALLBACK


def test_first_tag_wins_when_both_exist(cf):
    usgaap(cf)["ProfitLoss"] = copy.deepcopy(usgaap(cf)["NetIncomeLoss"])
    usgaap(cf)["ProfitLoss"]["units"]["USD"][2]["val"] = 777
    comp = concept_as_of(cf, NET_INCOME, FY19, NEXT_DAY)
    assert comp.status == FOUND and comp.value == 100 and comp.note == "NetIncomeLoss"


def test_missing_stays_missing(cf):
    del usgaap(cf)["AssetsCurrent"]
    ind = indicators_as_of(cf, FY19, NEXT_DAY)["current_ratio"]
    assert ind.status == MISSING and ind.value is None


def test_wrong_unit_counts_as_missing(cf):
    usgaap(cf)["Assets"]["units"]["EUR"] = usgaap(cf)["Assets"]["units"].pop("USD")
    assert indicators_as_of(cf, FY19, NEXT_DAY)["return_on_assets"].status == MISSING


# ---------- every ratio, by hand ----------
def test_indicator_arithmetic(cf):
    ind = indicators_as_of(cf, FY19, NEXT_DAY)
    assert ind["net_margin"].value == pytest.approx(100 / 1000)  # 0.10
    assert ind["return_on_assets"].value == pytest.approx(100 / 2000)  # 0.05
    assert ind["operating_cash_flow"].value == 150
    assert ind["free_cash_flow"].value == 150 - 50  # 100
    assert ind["fcf_margin"].value == pytest.approx(100 / 1000)  # 0.10
    assert ind["current_ratio"].value == pytest.approx(600 / 400)  # 1.5
    # no Liabilities tag → derived fallback: 2000 − 800 = 1200; ÷ assets 2000 = 0.6
    assert ind["liabilities_to_assets"].value == pytest.approx(0.6)
    assert ind["liabilities_to_assets"].status == FALLBACK
    assert {k: v.status for k, v in ind.items() if k != "liabilities_to_assets"} == dict.fromkeys(
        [k for k in ind if k != "liabilities_to_assets"], FOUND
    )


def test_direct_liabilities_tag_preferred(cf):
    usgaap(cf)["Liabilities"] = {
        "units": {"USD": [{**usgaap(cf)["Assets"]["units"]["USD"][2], "val": 1100}]}
    }
    ind = indicators_as_of(cf, FY19, NEXT_DAY)["liabilities_to_assets"]
    assert ind.status == FOUND and ind.value == pytest.approx(1100 / 2000)


def test_division_by_zero_is_missing(cf):
    usgaap(cf)["LiabilitiesCurrent"]["units"]["USD"][0]["val"] = 0
    assert indicators_as_of(cf, FY19, NEXT_DAY)["current_ratio"].status == MISSING


# ---------- earnings stability ----------
def test_eps_growth_stdev_uses_same_filing_pairs_across_a_split(cf):
    # pairs (latest filing with both years): 2015/2014 A16 +0.10 · 2016/2015 A17 −0.10 · 2017/2016 A18 +0.20 ·
    # 2018/2017 A19 0.00 · 2019/2018 A19 −0.10 (A19 values are halved by a 2:1 split — same basis within the pair)
    # mean 0.02; squared deviations .0064 .0144 .0324 .0004 .0144 = .068; ÷ 4 = .017; √ = 0.130384…
    ind = eps_growth_stdev(cf, FY19, NEXT_DAY)
    assert ind.status == FOUND
    assert ind.value == pytest.approx(math.sqrt(0.017))
    # mixing filings (2017 from A19 = 0.594 vs 2016 from A18 = 0.99) would have given −0.40 — not used
    assert "-0.4000" not in ind.note


def test_eps_growth_stdev_missing_when_too_few_years_known(cf):
    # on the A18 filing's next day only 2014..2018 are known → 5 years = 4 growths → MISSING
    assert eps_growth_stdev(cf, date(2018, 12, 31), date(2019, 2, 16)).status == MISSING


def test_eps_growth_stdev_falls_back_to_basic_eps(cf):
    usgaap(cf)["EarningsPerShareBasic"] = usgaap(cf).pop("EarningsPerShareDiluted")
    ind = eps_growth_stdev(cf, FY19, NEXT_DAY)
    assert ind.status == FALLBACK and ind.value == pytest.approx(math.sqrt(0.017))


def test_eps_previous_zero_is_missing(cf):
    for row in usgaap(cf)["EarningsPerShareDiluted"]["units"]["USD/shares"]:
        if row["end"] == "2018-12-31" and row["accn"] == "A19":
            row["val"] = 0
    assert eps_growth_stdev(cf, FY19, NEXT_DAY).status == MISSING


# ---------- fiscal years ----------
def test_fiscal_years_one_per_original_10k(cf):
    fys = fiscal_years(cf, min_facts=1)  # the tiny fixture has few facts per year
    assert [(f.end, f.filed, f.accn) for f in fys] == [
        (date(2016, 12, 31), date(2017, 2, 17), "A16"),
        (date(2017, 12, 31), date(2018, 2, 16), "A17"),
        (date(2018, 12, 31), date(2019, 2, 15), "A18"),
        (date(2019, 12, 31), date(2020, 2, 14), "A19"),
    ]
    assert fys[-1].usable_from == NEXT_DAY


def test_fiscal_year_ignores_a_stray_fact_dated_after_the_filing(cf):
    rows = usgaap(cf)["Revenues"]["units"]["USD"]
    rows.append(
        {**rows[2], "start": "2020-01-01", "end": "2020-12-31", "val": 1}
    )  # in A19, filed 2020-02-14
    assert [f.end for f in fiscal_years(cf, min_facts=1)][-1] == FY19  # not 2020-12-31


def test_fiscal_year_end_needs_enough_facts(cf):
    # default 5: only A19's 2019-12-31 has 5 annual duration facts (revenue, NI, OCF, capex, EPS)
    assert [(f.end, f.accn) for f in fiscal_years(cf)] == [(FY19, "A19")]


def test_liabilities_second_fallback_only_without_nci(cf):
    g = usgaap(cf)
    g["StockholdersEquity"] = g.pop(
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"
    )
    comp = indicators_as_of(cf, FY19, NEXT_DAY)["liabilities_to_assets"]
    assert comp.status == FALLBACK and comp.value == pytest.approx((2000 - 800) / 2000)
    assert "ASSUMPTION" in comp.components[0].note
    # once a non-controlling interest is tagged for that date, we cannot know liabilities → MISSING
    g["MinorityInterest"] = {
        "units": {"USD": [{**g["StockholdersEquity"]["units"]["USD"][0], "val": 30}]}
    }
    assert indicators_as_of(cf, FY19, NEXT_DAY)["liabilities_to_assets"].status == MISSING


def test_revenue_tags_that_disagree_are_a_conflict(cf):
    g = usgaap(cf)
    g["SalesRevenueNet"] = copy.deepcopy(g["Revenues"])
    g["SalesRevenueNet"]["units"]["USD"][2]["val"] = 1004  # 0.4% apart → agree, first tag used
    assert concept_as_of(cf, REVENUE, FY19, NEXT_DAY).value == 1000
    g["SalesRevenueNet"]["units"]["USD"][2]["val"] = 2900  # far apart → CONFLICT, never picked
    comp = concept_as_of(cf, REVENUE, FY19, NEXT_DAY)
    assert comp.status == CONFLICT and "disagree" in comp.note
    # goods-only revenue is not cross-checked (a narrower concept)
    g.pop("SalesRevenueNet")
    g["SalesRevenueGoodsNet"] = copy.deepcopy(g["Revenues"])
    g["SalesRevenueGoodsNet"]["units"]["USD"][2]["val"] = 600
    assert concept_as_of(cf, REVENUE, FY19, NEXT_DAY).value == 1000
