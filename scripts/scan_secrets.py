"""Scan the WHOLE git history (every branch and tag) for secrets and licensed data (Phase 10, Step 10.3).

Run:  uv run python scripts/scan_secrets.py            (exit code 1 if anything is found)
Checks every file version ever committed (all blobs reachable from any ref) and every commit's author / committer:
- the real Tiingo key and SEC User-Agent from .env (read, never printed);
- generic secret shapes: key/token/secret/password = <long value>, GitHub / AWS / OpenAI-style tokens, private keys;
- email addresses — allowed only: the GitHub noreply address and the reserved test domains of RFC 2606
  (example.com/org/net, .example, .invalid, .test — never real mailboxes; used for fake test identities);
- licensed data: any path under data/, any .env file, any Excel file, any CSV with > 100 price-like rows.
Findings show the commit-reachable path and the KIND of match only — a matched secret is never printed.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_EMAIL = re.compile(
    r"@users\.noreply\.github\.com$|@example\.(com|org|net)$|\.(example|invalid|test)$",
    re.IGNORECASE,
)
EMAIL = re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SECRET_SHAPES = {
    "key/token assignment": re.compile(
        rb"(?i)(api[_-]?key|secret|token|passw(or)?d)[\"']?\s*[:=]\s*[\"']?(?!your_key_here)[A-Za-z0-9_\-]{20,}"
    ),
    "GitHub token": re.compile(rb"gh[pousr]_[A-Za-z0-9]{36,}"),
    "AWS access key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "OpenAI/Anthropic-style key": re.compile(rb"sk-(ant-)?[A-Za-z0-9_\-]{20,}"),
    "private key": re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}
# The scanner's own self-test contains FAKE secret shapes and a FAKE ordinary email on purpose (commit 4447f20; built
# from pieces since). Shape and email checks skip that one file; the checks for the REAL values from .env still cover it.
SHAPE_EXEMPT = {"tests/test_scan_secrets.py"}
PRICE_ROW = re.compile(rb"^\d{4}-\d{2}-\d{2}[^\n]*?,\d+(\.\d+)?,\d+(\.\d+)?", re.MULTILINE)


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=PROJECT_ROOT, check=True, capture_output=True).stdout


def blobs() -> dict[str, set[str]]:
    """blob sha → every path it was committed under, over all refs."""
    out: dict[str, set[str]] = {}
    for line in git("rev-list", "--objects", "--all").decode().splitlines():
        sha, _, path = line.partition(" ")
        if path:
            out.setdefault(sha, set()).add(path)
    return out


def read_blobs(shas: list[str]) -> dict[str, bytes]:
    """Contents of the given objects (only blobs are returned)."""
    proc = subprocess.run(["git", "cat-file", "--batch"], cwd=PROJECT_ROOT, input="\n".join(shas).encode() + b"\n",
                          check=True, capture_output=True)  # fmt: skip
    data, pos, out = proc.stdout, 0, {}
    while pos < len(data):
        header_end = data.index(b"\n", pos)
        sha, kind, size = data[pos:header_end].decode().split()
        start = header_end + 1
        if kind == "blob":
            out[sha] = data[start : start + int(size)]
        pos = start + int(size) + 1
    return out


def main() -> int:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    env = dotenv_values(PROJECT_ROOT / ".env")
    real = {name: (env.get(name) or "").strip() for name in ("TIINGO_API_KEY", "SEC_USER_AGENT")}
    real_email = re.search(r"[\w.%+-]+@[\w.-]+", real["SEC_USER_AGENT"])
    exact = {"TIINGO_API_KEY (real value)": real["TIINGO_API_KEY"].encode()}
    if real_email:
        exact["SEC_USER_AGENT email (real value)"] = real_email.group(0).encode()
    exact = {k: v for k, v in exact.items() if len(v) >= 6}
    refs = git("for-each-ref", "--format=%(refname)").decode().split()
    commits = git("rev-list", "--all").decode().split()
    paths = blobs()
    contents = read_blobs(sorted(paths))
    findings: list[str] = []
    for line in git("log", "--all", "--format=%H %ae %ce").decode().splitlines():
        sha, *emails = line.split()
        for e in set(emails):
            if not ALLOWED_EMAIL.search(e):
                findings.append(
                    f"commit {sha[:7]}: author/committer email is not the GitHub noreply address"
                )
    for sha, body in contents.items():
        where = ", ".join(sorted(paths[sha]))
        for label, value in exact.items():
            if value in body:
                findings.append(f"{where}: contains the {label}")
        for label, pattern in SECRET_SHAPES.items():
            if paths[sha] <= SHAPE_EXEMPT:
                continue
            if pattern.search(body):
                findings.append(f"{where}: looks like a {label}")
        emails = (
            set()
            if paths[sha] <= SHAPE_EXEMPT
            else {m.group(0).decode(errors="replace") for m in EMAIL.finditer(body)}
        )
        for e in emails:
            if not ALLOWED_EMAIL.search(e) and not e.endswith((".png", ".jpg", ".svg")):
                findings.append(
                    f"{where}: contains an email address (not shown) on domain {e.split('@')[-1]}"
                )
        for p in paths[sha]:
            low = p.lower()
            if low.startswith("data/") or "/data/raw" in low:
                findings.append(f"{p}: file under data/ was committed")
            if Path(low).name == ".env":
                findings.append(f"{p}: a .env file was committed")
            if low.endswith((".xls", ".xlsx")):
                findings.append(f"{p}: an Excel file was committed")
            if low.endswith(".csv") and len(PRICE_ROW.findall(body)) > 100:
                findings.append(f"{p}: CSV with {len(PRICE_ROW.findall(body))} price-like rows")
    print(f"refs scanned: {len(refs)} ({sum(r.startswith('refs/tags/') for r in refs)} tags) · commits: {len(commits)} · "
          f"file versions (blobs): {len(contents)} · real secrets checked from .env: {len(exact)}")  # fmt: skip
    findings = sorted(set(findings))
    print(f"findings: {len(findings)}")
    for f in findings:
        print("  -", f)
    return 1 if findings else 0


if __name__ == "__main__":
    os.chdir(PROJECT_ROOT)
    sys.exit(main())
