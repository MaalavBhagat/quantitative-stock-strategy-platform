"""Download the RBA daily exchange-rate files for 2010–2017 once (DATA_SOURCES §9).

Run:  uv run python scripts/download_rba_fx.py
Refuses to overwrite existing files. Writes a .meta.json next to each file.
"""

import sys
import urllib.request

from quant_research.data.fx import DEFAULT_RBA_DIR, RBA_BASE_URL, RBA_FILES, now_utc, write_meta


def main() -> int:
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
