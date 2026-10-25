"""AUD/USD exchange rates from the RBA (DATA_SOURCES §9) — for portfolio start/end conversion.

Files: RBA historical daily exchange rates (.xls, sheet "Data"), saved under /data/raw/rba/ with a
.meta.json. Column = Series ID "FXRUSD" ("A$1=USD", WM/Reuters 4 pm Sydney). Licence: personal,
non-commercial use, attributed to the RBA — never committed.
Timing rule [ASSUMPTION]: conversion on US trading day T uses the latest RBA rate dated ≤ T
(4 pm Sydney is before the US open of the same calendar day). Gaps > 5 calendar days → error.
"""

import bisect
import itertools
import json
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import xlrd

from quant_research.portfolio.money import require_decimal

logger = logging.getLogger(__name__)

DEFAULT_RBA_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "rba"
RBA_BASE_URL = "https://www.rba.gov.au/statistics/tables/xls-hist/"
RBA_FILES = ["2010-2013.xls", "2014-2017.xls"]
USD_SERIES_ID = "FXRUSD"
MAX_GAP_DAYS = 5
PLAUSIBLE = (Decimal("0.40"), Decimal("1.20"))


class FxDataError(ValueError):
    """Exchange-rate data missing, stale or implausible."""


def parse_rba_xls(path: Path) -> list[tuple[date, Decimal]]:
    """(date, usd_per_aud) rows from one RBA .xls file. Blank / "N/A" cells are skipped (no rate)."""
    book = xlrd.open_workbook(str(path))
    sheet = book.sheet_by_name("Data")
    id_row = next(
        (
            r
            for r in range(min(20, sheet.nrows))
            if str(sheet.cell_value(r, 0)).strip() == "Series ID"
        ),
        None,
    )
    if id_row is None:
        raise FxDataError(f"{path.name}: no 'Series ID' row found")
    ids = [str(sheet.cell_value(id_row, c)).strip() for c in range(sheet.ncols)]
    if USD_SERIES_ID not in ids:
        raise FxDataError(f"{path.name}: series {USD_SERIES_ID} not found")
    col = ids.index(USD_SERIES_ID)
    rows, blanks = [], 0
    for r in range(id_row + 1, sheet.nrows):
        date_cell, value_cell = sheet.cell(r, 0), sheet.cell(r, col)
        if date_cell.ctype != xlrd.XL_CELL_DATE:
            raise FxDataError(
                f"{path.name} row {r}: first column is not a date ({date_cell.value!r})"
            )
        day = xlrd.xldate_as_datetime(date_cell.value, book.datemode).date()
        # Blank or the RBA's own "N/A" marker = no rate published that day (e.g. 2015-05-25,
        # a US holiday). Skipped, counted and logged — never filled.
        if value_cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK) or str(
            value_cell.value
        ).strip() in ("", "N/A"):
            blanks += 1
            logger.info("%s: no USD rate on %s (%r) — skipped", path.name, day, value_cell.value)
            continue
        if value_cell.ctype != xlrd.XL_CELL_NUMBER:
            raise FxDataError(
                f"{path.name} {day}: USD value is not a number ({value_cell.value!r})"
            )
        rows.append((day, Decimal(repr(float(value_cell.value)))))
    if blanks:
        logger.info("%s: %d days without a USD rate (skipped, not filled)", path.name, blanks)
    return rows


@dataclass(frozen=True)
class FxSeries:
    """Validated, sorted daily usd_per_aud rates."""

    dates: tuple[date, ...]
    rates: tuple[Decimal, ...]
    source_files: tuple[str, ...] = ()

    def on(self, day: date) -> Decimal:
        """Latest rate dated ≤ day. Error if before the first rate or more than 5 days stale."""
        i = bisect.bisect_right(self.dates, day) - 1
        if i < 0:
            raise FxDataError(f"no AUD/USD rate on or before {day} (series starts {self.dates[0]})")
        if (day - self.dates[i]).days > MAX_GAP_DAYS:
            raise FxDataError(
                f"latest AUD/USD rate before {day} is from {self.dates[i]} — more than {MAX_GAP_DAYS} days old"
            )
        if self.dates[i] != day:
            logger.debug("no RBA rate on %s — using %s", day, self.dates[i])
        return self.rates[i]


def build_series(rows: list[tuple[date, Decimal]], source_files: tuple[str, ...] = ()) -> FxSeries:
    """Validate rows: sorted, no duplicates, positive, plausible range (row gaps are logged)."""
    if not rows:
        raise FxDataError("no exchange-rate rows")
    dates = [d for d, _ in rows]
    if dates != sorted(dates):
        raise FxDataError("exchange-rate dates are not sorted")
    if len(set(dates)) != len(dates):
        dup = next(d for d in dates if dates.count(d) > 1)
        raise FxDataError(f"duplicate exchange-rate date {dup}")
    for d, rate in rows:
        require_decimal(rate, f"rate on {d}")
        if not PLAUSIBLE[0] <= rate <= PLAUSIBLE[1]:
            raise FxDataError(f"AUD/USD rate {rate} on {d} outside plausible range {PLAUSIBLE}")
    # Gaps between RBA rows (Sydney holidays, e.g. Easter + Anzac Day 2011 = 6 days) are only logged:
    # the 5-day limit applies where it matters — at lookup for a trading day (FxSeries.on).
    for prev, cur in itertools.pairwise(dates):
        if (cur - prev).days > MAX_GAP_DAYS:
            logger.info("RBA rows %s → %s are %d days apart", prev, cur, (cur - prev).days)
    return FxSeries(tuple(dates), tuple(r for _, r in rows), source_files)


TRIM_CUTOFF = date(2020, 12, 31)  # RBA 2018-2022.xls is kept only up to here (D8, Goggy 2026-10-25)


def parse_trimmed_csv(path: Path) -> list[tuple[date, Decimal]]:
    """(date, usd_per_aud) rows from a trimmed RBA extract (CSV: date,usd_per_aud). Must end ≤ 2020-12-31."""
    import csv

    with path.open(encoding="utf-8") as handle:
        rows = [
            (date.fromisoformat(r["date"]), Decimal(r["usd_per_aud"]))
            for r in csv.DictReader(handle)
        ]
    if rows and max(d for d, _ in rows) > TRIM_CUTOFF:
        raise FxDataError(
            f"{path.name} contains dates after {TRIM_CUTOFF} — final-test data must not be on disk"
        )
    return rows


def trim_rba_xls(source: Path, out_csv: Path, url: str, downloaded_at_utc: str) -> Path:
    """Write ONLY the rows dated ≤ 2020-12-31 of an RBA .xls to out_csv (+ .meta.json). Source is not kept here."""
    import csv

    rows = parse_rba_xls(source)
    kept = [(d, r) for d, r in rows if d <= TRIM_CUTOFF]
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "usd_per_aud"])
        writer.writerows((d.isoformat(), str(r)) for d, r in kept)
    meta = {
        "source": "Reserve Bank of Australia — historical daily exchange rates",
        "url": url,
        "downloaded_at_utc": downloaded_at_utc,
        "sheet": "Data",
        "series_id": USD_SERIES_ID,
        "original_file": source.name,
        "original_rows_with_usd_rate": len(rows),
        "original_last_date": str(rows[-1][0]),
        "trimmed_to": str(TRIM_CUTOFF),
        "rows_kept": len(kept),
        "first_date": str(kept[0][0]),
        "last_date": str(kept[-1][0]),
        "rows_dropped_after_cutoff": len(rows) - len(kept),
        "note": "Trimmed at download (Goggy 2026-10-25): rows after 2020-12-31 were never saved here and the original "
        "file was deleted, so no final-test-period (D8) rate is on disk. Values unchanged (FXRUSD).",
        "licence_note": "RBA: personal, non-commercial use, attributed — never commit",
    }
    meta_path = out_csv.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta_path


def load_usd_per_aud(data_dir: Path = DEFAULT_RBA_DIR) -> FxSeries:
    """Read every RBA .xls (and trimmed .csv) in data_dir (each needs its .meta.json) into one validated series."""
    files = sorted([*data_dir.glob("*.xls"), *data_dir.glob("*.csv")])
    if not files:
        raise FxDataError(
            f"no RBA files in {data_dir} — run `uv run python scripts/download_rba_fx.py`"
        )
    rows: list[tuple[date, Decimal]] = []
    for path in files:
        if not path.with_suffix(".meta.json").exists():
            raise FxDataError(
                f"{path.name} has no .meta.json — data without a download record is not used"
            )
        rows += parse_rba_xls(path) if path.suffix == ".xls" else parse_trimmed_csv(path)
    return build_series(sorted(rows), tuple(p.name for p in files))


def write_meta(path: Path, url: str, downloaded_at_utc: str, note: str | None = None) -> Path:
    """Write the download record next to an RBA file."""
    rows = parse_rba_xls(path)
    meta = {
        "source": "Reserve Bank of Australia — historical daily exchange rates",
        "url": url,
        "downloaded_at_utc": downloaded_at_utc,
        "sheet": "Data",
        "series_id": USD_SERIES_ID,
        "rows_with_usd_rate": len(rows),
        "first_date": str(rows[0][0]),
        "last_date": str(rows[-1][0]),
        "licence_note": "RBA: personal, non-commercial use, unaltered, attributed — never commit",
    }
    if note:
        meta["note"] = note
    meta_path = path.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta_path


def now_utc() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
