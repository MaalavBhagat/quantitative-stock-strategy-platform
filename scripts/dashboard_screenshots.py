"""Phase 8: save one screenshot per dashboard page into data/screenshots/ (git-ignored: shows licensed prices).

Needs the dashboard running on localhost:8501 (README "How to open the dashboard") and the project-local browser:
  PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers uv run --group screenshots python scripts/dashboard_screenshots.py
Pages showing a run use S4-S2 · AAPL · X 2% / Y 4% (validation) — the run checked against the validation report.
It also presses "Generate report + export files" (→ data/exports/) and starts ONE exploratory lab run
(→ data/runs/lab/, labelled EXPLORATORY — NOT PRE-REGISTERED).
With --demo it ONLY saves docs/images/dashboard_demo_{overview,performance,trades}.png: the dashboard on the MADE-UP
demo data (run `uv run python scripts/demo.py` first) — safe to commit and publish, unlike the real-data screenshots.
With --dropdown it ONLY saves data/screenshots/0_overview_dropdown.png (the Overview strategy menu opened, showing
the plain-English names) — no export, no lab run.
"""

import os
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT = PROJECT_ROOT / "data" / "screenshots"
URL = "http://localhost:8501"
PAGES = [("1_overview", "Overview"), ("2_company", "Company research"), ("3_performance", "Performance"),
         ("4_trades", "Trade explorer")]  # fmt: skip


def settle(page: Page) -> None:
    """Wait until Streamlit has finished running the script (no 'Running…' status) and charts have drawn."""
    page.wait_for_load_state("networkidle")
    page.wait_for_function(
        "() => !document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=120_000
    )
    page.wait_for_timeout(1500)


def choose(page: Page, label: str, option: str) -> None:
    box = page.get_by_role("combobox", name=label)
    box.click(
        force=True
    )  # Streamlit overlays the box while it redraws; the click itself is the same
    box.fill(option)
    box.press("Enter")
    settle(page)
    if box.input_value() != option:
        raise SystemExit(f"could not choose {option!r} in {label!r} (shows {box.input_value()!r})")


def dropdown_only(page: Page) -> None:
    """Overview with the sidebar strategy menu open (labels shown as 'Name (ID)')."""
    choose(page, "Strategy", "Trend filter + pullback (S4-S2)")
    page.get_by_role("combobox", name="Strategy").click(force=True)
    page.wait_for_timeout(800)
    path = OUT / "0_overview_dropdown.png"
    page.screenshot(path=str(path))
    options = page.get_by_role("option").all_inner_texts()
    print(f"saved {path.relative_to(PROJECT_ROOT)} — menu options: {options}")


DEMO_OUT = PROJECT_ROOT / "docs" / "images"


def demo_only(page: Page) -> None:
    """Dashboard on the made-up demo runs only (period 'demo'): Overview, Performance, Trade explorer."""
    page.get_by_text("demo", exact=True).click(force=True)
    settle(page)
    choose(page, "Strategy", "Trend filter + pullback (S4-S2)")
    DEMO_OUT.mkdir(parents=True, exist_ok=True)
    for name, title in (
        ("overview", "Overview"),
        ("performance", "Performance"),
        ("trades", "Trade explorer"),
    ):
        page.get_by_role("link", name=title, exact=True).click(force=True)
        settle(page)
        if "MADE-UP" not in page.inner_text("body"):
            raise SystemExit(
                f"{title}: the demo banner is missing — refusing to save a possibly real-data screenshot"
            )
        path = DEMO_OUT / f"dashboard_demo_{name}.png"
        page.screenshot(path=str(path))
        print(
            f"saved {path.relative_to(PROJECT_ROOT)} — page heading: {page.locator('h1').first.inner_text()}"
        )


def main() -> int:
    if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(PROJECT_ROOT / ".playwright-browsers")
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 2200})
        page.goto(URL)
        settle(page)
        if "--demo" in sys.argv:
            page.set_viewport_size({"width": 1440, "height": 1500})
            demo_only(page)
            browser.close()
            return 0
        if "--dropdown" in sys.argv:
            dropdown_only(page)
            browser.close()
            return 0
        choose(page, "Strategy", "Trend filter + pullback (S4-S2)")
        choose(page, "Setting", "X 2% / Y 4%")
        for name, title in PAGES:
            page.get_by_role("link", name=title, exact=True).click(force=True)
            settle(page)
            path = OUT / f"{name}.png"
            page.screenshot(path=str(path))
            heading = page.locator("h1").first.inner_text()
            print(f"saved {path.relative_to(PROJECT_ROOT)} — page heading: {heading}")
        # 5: report + exports for the same saved run
        page.get_by_role("link", name="Report & export", exact=True).click(force=True)
        settle(page)
        page.get_by_role("button", name="Generate report + export files").click(force=True)
        settle(page)
        page.screenshot(path=str(OUT / "5_report.png"))
        print(
            f"saved data/screenshots/5_report.png — page heading: {page.locator('h1').first.inner_text()}"
        )
        # 6: one exploratory lab run (S4-S2 · AAPL · validation · main · X 2% / Y 4%) through run.py
        page.get_by_role("link", name="Strategy lab", exact=True).click(force=True)
        settle(page)
        page.get_by_text("validation", exact=True).click(force=True)
        settle(page)
        choose(page, "Strategy", "Trend filter + pullback (S4-S2)")
        page.get_by_role(
            "button", name="Run (through run.py) — plus Buy-and-hold (S0) with the same settings"
        ).click(force=True)
        settle(page)
        page.screenshot(path=str(OUT / "6_lab.png"))
        print(
            f"saved data/screenshots/6_lab.png — page heading: {page.locator('h1').first.inner_text()}"
        )
        browser.close()
    return 0


if __name__ == "__main__":
    from _help import handle_help  # --help: describe and exit, do nothing else

    handle_help(__doc__)
    sys.exit(main())
