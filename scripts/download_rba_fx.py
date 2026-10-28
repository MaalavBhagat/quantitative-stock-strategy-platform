"""Download the RBA daily exchange-rate files for 2010–2017 once (DATA_SOURCES §9).

Run:  uv run python scripts/download_rba_fx.py
      uv run python scripts/download_rba_fx.py --final-test   # 2021–2025 only (research/FINAL_TEST_PREREG.md)
Refuses to overwrite existing files. Writes a .meta.json next to each file.
--final-test: the official 2018-2022.xls and 2023-current.xls are downloaded to a temporary folder; only the rows
2021-01-01 … 2022-12-31 and 2023-01-01 … 2025-12-31 are saved (trimmed CSV + .meta.json) and the originals are
deleted, so nothing after 2025-12-31 is ever on disk (2018–2020 rows are already in 2018-2020_from_2018-2022.csv).
"""

import sys
import tempfile
import urllib.request
from datetime import date
from pathlib import Path

from quant_research.data.fx import (
    DEFAULT_RBA_DIR,
    FINAL_CUTOFF,
    RBA_BASE_URL,
    RBA_FILES,
    now_utc,
    trim_rba_xls,
    write_meta,
)

FINAL_FILES = [  # (official file, saved extract, keep from, keep to)
    ("2018-2022.xls", "2021-2022_from_2018-2022.csv", date(2021, 1, 1), date(2022, 12, 31)),
    ("2023-current.xls", "2023-2025_from_2023-current.csv", date(2023, 1, 1), FINAL_CUTOFF),
]


def final_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        for name, out_name, keep_from, keep_to in FINAL_FILES:
            out = DEFAULT_RBA_DIR / out_name
            if out.exists():
                print(f"{out_name}: already saved — not overwritten")
                continue
            source, url = Path(tmp) / name, RBA_BASE_URL + name
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request) as response:  # fixed official RBA URL
                source.write_bytes(response.read())
            meta = trim_rba_xls(source, out, url, now_utc(), keep_from=keep_from, cutoff=keep_to)
            source.unlink()
            print(f"{name} → {out_name} (+ {meta.name}); original deleted")
    return 0


def main() -> int:
    if "--final-test" in sys.argv:
        return final_test()
    DEFAULT_RBA_DIR.mkdir(parents=True, exist_ok=True)
    for name in RBA_FILES:
        path = DEFAULT_RBA_DIR / name
        url = RBA_BASE_URL + name
        if path.exists():
            print(f"{name}: already downloaded — not overwritten")
            continue
        urllib.request.urlretrieve(url, path)  # fixed official RBA URL
        meta = write_meta(path, url, now_utc())
        print(f"{name}: downloaded, record {meta.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
