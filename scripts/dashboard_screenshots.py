"""Phase 8: save one screenshot per dashboard page into data/screenshots/ (git-ignored: shows licensed prices).

Needs the dashboard running on localhost:8501 (README "How to open the dashboard") and the project-local browser:
  PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers uv run --group screenshots python scripts/dashboard_screenshots.py
Pages showing a run use S4-S2 · AAPL · X 2% / Y 4% (validation) — the run checked against the validation report.
It also presses "Generate report + export files" (→ data/exports/) and starts ONE exploratory lab run
(→ data/runs/lab/, labelled EXPLORATORY — NOT PRE-REGISTERED).
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


def main() -> int:
    if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(PROJECT_ROOT / ".playwright-browsers")
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 2200})
        page.goto(URL)
        settle(page)
        choose(page, "Strategy", "S4-S2")
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
        choose(page, "Strategy", "S4-S2")
        page.get_by_role(
            "button", name="Run (through run.py) — plus S0 with the same settings"
        ).click(force=True)
        settle(page)
        page.screenshot(path=str(OUT / "6_lab.png"))
        print(
            f"saved data/screenshots/6_lab.png — page heading: {page.locator('h1').first.inner_text()}"
        )
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
