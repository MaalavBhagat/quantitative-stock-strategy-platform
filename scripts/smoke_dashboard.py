"""Phase 8 smoke check: load every dashboard page once, headless (Streamlit AppTest — no browser, no server).

Run:  uv run --group dashboard python scripts/smoke_dashboard.py
Prints, per page: errors / exceptions found (must be 0) and the banner text shown.
"""

import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

PAGES = (
    Path(__file__).resolve().parents[1] / "src" / "quant_research" / "dashboard" / "app" / "pages"
)


def main() -> int:
    bad = 0
    for name in ["overview", "company", "performance", "trades"]:
        at = AppTest.from_file(str(PAGES / f"{name}.py"), default_timeout=120).run()
        errors = [e.value for e in at.exception] + [
            e.value for e in at.error if "REJECTED" not in e.value
        ]
        banners = [w.value for w in at.warning if "SIMULATED, HISTORICAL" in w.value]
        print(
            f"{name}: exceptions/errors {len(errors)} · banner: {banners[0] if banners else 'MISSING'}"
        )
        for e in errors:
            print("   ", str(e)[:300])
        bad += len(errors) + (0 if banners else 1)
    print("smoke check:", "PASS" if bad == 0 else f"FAIL ({bad})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
