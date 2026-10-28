"""Phase 9 Part D — AI labelling side test (EXPLORATORY: never part of any verdict, no trading use).

Question: how reliable is an AI (Claude Code) at reading an 8-K's TEXT and putting it into our categories, compared with
the filer's official item codes?

  uv run python scripts/ai_label_sample.py download   # 40 random 2010–2020 8-Ks (seed 20261028), ≤ 1 request/s
  uv run python scripts/ai_label_sample.py show       # prints the MASKED texts only (no item codes) for labelling
  (Claude Code writes reports/phase9/ai_labels_sample.json from the masked texts, following INSTRUCTION below)
  uv run python scripts/ai_label_sample.py compare    # → reports/phase9/ai_labels_sample.md

Masking: every "Item N.NN" code and every official Form 8-K item title is replaced by [HIDDEN] before labelling; the
official codes are kept in data/raw/sec/8k_text_sample/sample.json (git-ignored) and only read by `compare`.
Only the PRIMARY document is used (exhibits such as press releases are not downloaded). The User-Agent comes from .env
(SEC_USER_AGENT) and is never printed or saved. SEC filings are public information (cite SEC).
"""

import html
import json
import os
import random
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import httpx
from dotenv import load_dotenv

from quant_research.data.sec import Throttle
from quant_research.news.events import CATEGORY, EXHIBITS_ONLY, filing_categories

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUB = PROJECT_ROOT / "data" / "raw" / "sec" / "submissions"
OUT = PROJECT_ROOT / "data" / "raw" / "sec" / "8k_text_sample"
LABELS = PROJECT_ROOT / "reports" / "phase9" / "ai_labels_sample.json"
REPORT = PROJECT_ROOT / "reports" / "phase9" / "ai_labels_sample.md"
COMPANIES = ["AAPL", "MSFT", "KO", "PG", "XOM", "INTC", "T"]
SEED, N = 20261028, 40
SHOW_CHARS = 2500
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}"
CHOICES = sorted({*CATEGORY.values(), "other", EXHIBITS_ONLY})
INSTRUCTION = (
    "Read the text of this SEC Form 8-K primary document (item numbers and official item titles have been replaced by "
    "[HIDDEN]). Decide which of these categories the filing reports — one or more: "
    + "; ".join(CHOICES)
    + ". Use 'other' for a reportable event that fits none of the named categories, and 'exhibits only' only if the "
    "filing does nothing but furnish exhibits. Judge from what the text says happened, not from guesses about the "
    "company. Give the categories and one short reason."
)
# official Form 8-K item titles (SEC 873 (02-25)) — masked wherever they appear
TITLES = [
    "Entry into a Material Definitive Agreement", "Termination of a Material Definitive Agreement",
    "Bankruptcy or Receivership", "Mine Safety", "Material Cybersecurity Incidents",
    "Completion of Acquisition or Disposition of Assets", "Results of Operations and Financial Condition",
    "Creation of a Direct Financial Obligation", "Triggering Events That Accelerate or Increase",
    "Costs Associated with Exit or Disposal Activities", "Material Impairments", "Notice of Delisting",
    "Unregistered Sales of Equity Securities", "Material Modification to Rights of Security Holders",
    "Changes in Registrant's Certifying Accountant", "Non-Reliance on Previously Issued Financial Statements",
    "Changes in Control of Registrant", "Departure of Directors or Certain Officers",
    "Departure of Directors or Principal Officers", "Election of Directors", "Appointment of Certain Officers",
    "Compensatory Arrangements of Certain Officers", "Amendments to Articles of Incorporation or Bylaws",
    "Change in Fiscal Year", "Temporary Suspension of Trading Under Registrant's Employee Benefit Plans",
    "Amendment to Registrant's Code of Ethics", "Change in Shell Company Status",
    "Submission of Matters to a Vote of Security Holders", "Shareholder Director Nominations",
    "Regulation FD Disclosure", "Other Events", "Financial Statements and Exhibits",
]  # fmt: skip


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "table"):
            self.parts.append("\n")


def to_text(raw: str) -> str:
    p = _Text()
    p.feed(raw)
    text = html.unescape("".join(p.parts)).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def mask(text: str) -> str:
    text = re.sub(r"(?i)\bitems?\s*\d{1,2}\s*\.\s*\d{2}\b", "[HIDDEN]", text)
    for title in TITLES:
        text = re.sub(re.escape(title), "[HIDDEN]", text, flags=re.IGNORECASE)
    return text


def sample() -> list[dict]:
    rows = []
    for t in COMPANIES:
        [path] = sorted(SUB.glob(f"{t}_CIK*_8k_to-2020-12-31.json"))
        data = json.loads(path.read_text(encoding="utf-8"))
        for f in data["filings"]:
            if f["form"] == "8-K" and "2010-01-01" <= f["filingDate"] <= "2020-12-31":
                rows.append({"ticker": t, "cik": data["cik"], **f})
    rows.sort(key=lambda r: r["accessionNumber"])
    return random.Random(SEED).sample(rows, N)


def download() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    ua = os.environ.get("SEC_USER_AGENT", "")
    if "@" not in ua:
        print("SEC_USER_AGENT missing in .env")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    picked, throttle = sample(), Throttle()
    meta = []
    with httpx.Client(
        timeout=60.0, headers={"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}
    ) as http:
        for n, f in enumerate(picked, start=1):
            url = ARCHIVE.format(cik=int(f["cik"]), accession=f["accessionNumber"].replace("-", ""),
                                 document=f["primaryDocument"])  # fmt: skip
            throttle.wait()
            r = http.get(url)
            if r.status_code != 200:
                print(f"{n:2d} {f['accessionNumber']} HTTP {r.status_code}")
                return 1
            text = mask(to_text(r.text))
            (OUT / f"{n:02d}_{f['accessionNumber']}.txt").write_text(text, encoding="utf-8")
            meta.append({"n": n, "ticker": f["ticker"], "accession": f["accessionNumber"],
                         "filed": f["filingDate"], "url": url, "items": f["items"]})  # fmt: skip
            print(f"{n:2d} {f['ticker']:4s} {f['accessionNumber']} {len(text):6,d} chars (masked)")
    (OUT / "sample.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return 0


def show() -> int:
    """Masked texts for labelling: the part from the first hidden heading on (the cover page is boilerplate)."""
    print("INSTRUCTION:", INSTRUCTION, "\n")
    for path in sorted(OUT.glob("[0-9][0-9]_*.txt")):
        text = path.read_text(encoding="utf-8")
        start = text.find("[HIDDEN]")
        body = text[start:] if start >= 0 else text
        print(f"===== {path.stem} =====\n{body[:SHOW_CHARS]}\n")
    return 0


def official(items: str, accession: str) -> set[str]:
    cats = filing_categories({"accessionNumber": accession, "items": items})
    return {"other" if c.startswith("other (") else c for c in cats}


def leaked_titles(text: str) -> list[str]:
    """Official titles that survived masking because the document split them over a line break."""
    return [
        t for t in TITLES if re.search(r"\s+".join(map(re.escape, t.split())), text, re.IGNORECASE)
    ]


def compare() -> int:
    meta = {
        m["accession"]: m for m in json.loads((OUT / "sample.json").read_text(encoding="utf-8"))
    }
    lab = json.loads(LABELS.read_text(encoding="utf-8"))
    rows, exact, overlap = [], 0, 0
    for a in sorted(meta, key=lambda k: meta[k]["n"]):
        m, mine = meta[a], set(lab["labels"][a]["categories"])
        off = official(m["items"], a)
        exact += mine == off
        overlap += bool(mine & off)
        text = next(OUT.glob(f"{m['n']:02d}_*.txt")).read_text(encoding="utf-8")
        rows.append((m, mine, off, lab["labels"][a]["reason"], leaked_titles(text)))
    n = len(rows)
    out = [
        "# AI labelling side test — 40 SEC 8-Ks read by Claude Code vs the official item codes (Phase 9, Part D)",
        "",
        "> **EXPLORATORY — never part of any verdict; no trading use.** AI labels are interpretations, the item codes are",
        "> the filer's own (verified) facts. Generated by `scripts/ai_label_sample.py compare`.",
        "",
        f"- Model: {lab['model']} · labelled {lab['date']} · by {lab['who']}",
        f"- Sample: {n} Form 8-K filings 2010–2020 from AAPL, MSFT, KO, PG, XOM, INTC, T — random, seed {SEED}",
        "  (`random.Random(seed).sample` over all 8-Ks sorted by accession). Primary document only (no exhibits).",
        "- Masking before labelling: every 'Item N.NN' code and every official item title → [HIDDEN]. Official codes",
        "  were only read by `compare`, after the labels file was saved.",
        f"- Exact instruction used: “{INSTRUCTION}”",
        "",
        "## Result",
        "",
        f"- **Exact agreement** (same set of categories): **{exact}/{n} = {exact / n:.0%}**",
        f"- **At least one category in common**: {overlap}/{n} = {overlap / n:.0%}",
        "- Official categories use the same map as Phase 9 (news/events.py; official items without a named category",
        "  → 'other').",
        "",
        "## Every disagreement (for Goggy to spot-check 5 by hand — open the SEC link)",
        "",
        "| # | Company | Filed | AI label | Official (from item codes) | AI reason | SEC document |",
        "|---|---|---|---|---|---|---|",
    ]
    for m, mine, off, why, _ in rows:
        if mine != off:
            out.append(f"| {m['n']} | {m['ticker']} | {m['filed']} | {', '.join(sorted(mine))} | "
                       f"{', '.join(sorted(off))} (items {m['items']}) | {why} | {m['url']} |")  # fmt: skip
    leaks = [(m["n"], lk) for m, *_, lk in rows if lk]
    out += ["", f"**Masking leaks:** in {len(leaks)} of {n} documents an official title split over a line break was",
            "NOT masked, so it was visible while labelling (found afterwards by `compare`; the texts were not changed",
            "after labelling): " + ("; ".join(f"#{k}: {', '.join(v)}" for k, v in leaks) or "none") + "."]  # fmt: skip
    out += ["", "## All 40", "", "| # | Company | Filed | Accession | AI label | Official | Agree | Title leak |",
            "|---|---|---|---|---|---|---|---|"]  # fmt: skip
    for m, mine, off, _, lk in rows:
        out.append(f"| {m['n']} | {m['ticker']} | {m['filed']} | {m['accession']} | {', '.join(sorted(mine))} | "
                   f"{', '.join(sorted(off))} | {'yes' if mine == off else 'no'} | {'yes' if lk else '—'} |")  # fmt: skip
    out += ["", "Limitations: 40 filings is a small sample; only the primary document was read (press releases sit in",
            "exhibits); masking removes the most obvious give-aways but the wording of a filing can still echo its",
            "item title. Source: SEC EDGAR (public information).", ""]  # fmt: skip
    REPORT.write_text("\n".join(out), encoding="utf-8")
    print(
        f"agreement exact {exact}/{n}, overlap {overlap}/{n} → {REPORT.relative_to(PROJECT_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    from _help import handle_help  # --help: describe and exit, do nothing else

    handle_help(__doc__)
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit({"download": download, "show": show, "compare": compare}.get(command, lambda: 2)())
