"""The history scanner (scripts/scan_secrets.py) really detects what it looks for — fake values only."""

import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "scan_secrets", Path(__file__).resolve().parents[1] / "scripts" / "scan_secrets.py"
)
scan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scan)


def test_secret_shapes_are_detected():
    fake = {
        # built from pieces so this file itself never looks like a secret to the scanner
        "key/token assignment": b"TIINGO_API_" + b'KEY = "' + b"0123456789abcdef" * 2 + b'"',
        "GitHub token": b"gh" + b"p_" + b"a" * 36,
        "AWS access key": b"AK" + b"IA" + b"A" * 16,
        "OpenAI/Anthropic-style key": b"sk" + b"-ant-" + b"x" * 30,
        "private key": b"-----BEGIN RSA " + b"PRIVATE KEY-----",
    }
    for label, text in fake.items():
        assert scan.SECRET_SHAPES[label].search(text), label
    assert not scan.SECRET_SHAPES["key/token assignment"].search(b"TIINGO_API_KEY=your_key_here")
    # git commit hashes in reports are NOT flagged (no key=value shape)
    assert not any(
        p.search(b"commit 786e69940013d84230c855deb0401c441c1ba849")
        for p in scan.SECRET_SHAPES.values()
    )


def test_email_allow_list():
    assert scan.ALLOWED_EMAIL.search("12345+someone@users.noreply.github.com")
    assert scan.ALLOWED_EMAIL.search("bot@example.com") and scan.ALLOWED_EMAIL.search(
        "t@example.invalid"
    )
    assert not scan.ALLOWED_EMAIL.search("person@gmail.com")


def test_price_like_rows_are_counted():
    csv = b"date,open,close\n" + b"".join(
        b"2020-01-%02d,1.5,2.5\n" % (d % 28 + 1) for d in range(101)
    )
    assert len(scan.PRICE_ROW.findall(csv)) == 101
