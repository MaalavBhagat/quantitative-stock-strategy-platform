"""Phase 8 smoke check: load every dashboard page once, headless (Streamlit AppTest — no browser, no server).

Run:  uv run --group dashboard python scripts/smoke_dashboard.py
Prints, per page: errors / exceptions found (must be 0), the banner text shown, and any strategy ID shown WITHOUT
its plain-English name (must be none — strategies/labels.py).
"""

import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

from quant_research.strategies import labels

NOTICES = ("REJECTED", "EXPLORATORY — NOT PRE-REGISTERED")  # the app's own red notices, not errors
PAGES = (
    Path(__file__).resolve().parents[1] / "src" / "quant_research" / "dashboard" / "app" / "views"
)


def shown_text(at: AppTest) -> list[str]:
    """Every piece of text a page shows: headings, markdown, captions, metric labels, menu options, tables."""
    texts = [
        e.value
        for group in (
            at.title,
            at.header,
            at.subheader,
            at.markdown,
            at.caption,
            at.warning,
            at.error,
        )
        for e in group
    ]
    texts += [m.label for m in at.metric]
    for box in at.selectbox:
        texts += [box.label, *[str(o) for o in box.options]]
    for t in [*at.table, *at.dataframe]:
        df = t.value
        texts += [str(c) for c in df.columns] + [str(i) for i in df.index]
        texts += [str(v) for v in df.astype(str).to_numpy().ravel()]
    return texts


def main() -> int:
    bad = 0
    for name in ["overview", "company", "performance", "trades", "report", "lab"]:
        at = AppTest.from_file(str(PAGES / f"{name}.py"), default_timeout=120).run()
        errors = [e.value for e in at.exception] + [
            e.value for e in at.error if not any(n in e.value for n in NOTICES)
        ]
        banners = [w.value for w in at.warning if "SIMULATED, HISTORICAL" in w.value]
        bare = sorted({i for t in shown_text(at) for i in labels.bare_ids(t)})
        print(
            f"{name}: exceptions/errors {len(errors)} · banner: {banners[0] if banners else 'MISSING'}"
            f" · bare strategy IDs: {bare or 'none'}"
        )
        for e in errors:
            print("   ", str(e)[:300])
        bad += len(errors) + (0 if banners else 1) + len(bare)
    print("smoke check:", "PASS" if bad == 0 else f"FAIL ({bad})")
    return 1 if bad else 0


if __name__ == "__main__":
    from _help import handle_help  # --help: describe and exit, do nothing else

    handle_help(__doc__)
    sys.exit(main())
